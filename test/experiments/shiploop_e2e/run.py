#!/usr/bin/env python3
"""Opt-in one-shot Grok trials. Observe ShipLoop; never drive its callbacks.

The runner deliberately distinguishes process exit, declared SDLC completion,
skill selection, independently checked product behavior, and preservation.
It does not install skills, switch profiles, deploy, or send repair prompts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = Path(__file__).resolve().parent
# Kept separate so tests can exercise the observer guard against disposable
# sources without modifying the shared harness checkout.
OBSERVER_ROOT = HERE
sys.path.insert(0, str(HERE))
from capture import capture_process  # noqa: E402
from audit import summarize_trial  # noqa: E402
from behavior_capture import write_trial_behavior  # noqa: E402
from evidence import (  # noqa: E402
    capture_run_artifacts, compare_repos, inspect_run_artifacts,
    package_manifest, repo_snapshot,
)
from grading import validate_receipt, write_template  # noqa: E402
from grok_adapter import (  # noqa: E402
    build_argv,
    inspect_selection,
    observe_control_input_references,
    summarize_events,
)
from recovery_isolation import assess_isolation  # noqa: E402

# These public stop keys remain the v2 names used by suites.json. A v3
# navigator folds each prelude review into the accepted producer stage, so the
# compatibility aliases below resolve those keys after the selected state has
# established the protocol.
PARTIAL_STAGES = ("intake", "discovery", "research", "research-improve", "spec", "spec-improve",
                  "test-strategy", "plan", "plan-improve")
_V3_PARTIAL_STAGES = ("intake", "discovery", "research", "spec", "test-strategy", "plan")
_PARTIAL_STAGE_ALIASES = {
    2: {stage: stage for stage in PARTIAL_STAGES},
    3: {
        "intake": "intake",
        "discovery": "discovery",
        "research": "research",
        "research-improve": "research",
        "spec": "spec",
        "spec-improve": "spec",
        "test-strategy": "test-strategy",
        "plan": "plan",
        "plan-improve": "plan",
    },
}
_CONTROL_INPUT_OBSERVER_SCHEMA = 1
_OBSERVER_LATE_GRADE_SCHEMA = 1


def _partial_boundary(protocol_version: Any, requested_stage: str) -> tuple[str, tuple[str, ...]] | None:
    """Resolve a public partial-stop key against one observed navigator protocol.

    Protocol 3 accepts a producer stage only after its standalone Improve child
    returns. Its accepted ``plan`` is consequently the faithful counterpart of
    the legacy ``plan-improve`` boundary; no new physical ``prepare`` stop is
    exposed through the existing suite contract.
    """
    aliases = _PARTIAL_STAGE_ALIASES.get(protocol_version)
    if aliases is None:
        return None
    target = aliases.get(requested_stage)
    if target is None:
        return None
    stages = PARTIAL_STAGES if protocol_version == 2 else _V3_PARTIAL_STAGES
    return target, stages[:stages.index(target) + 1]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def candidate_digest(snapshot: dict) -> str:
    """Bind verification to source bytes, modes/index state, and repository HEAD."""
    value = {key: snapshot.get(key) for key in ("resolved_repo", "head", "branch", "status", "index", "files", "skipped")}
    caches = [row["path"] for row in snapshot.get("skipped", [])
              if row.get("reason") in {"runtime-cache-directory", "runtime-cache-file"}]
    if caches:
        # Omission diagnostics remain in the snapshot. Creating an excluded
        # cache must not make otherwise identical source a stale candidate.
        value["skipped"] = [row for row in snapshot["skipped"] if row["path"] not in caches]
        value["status"] = [row for row in snapshot.get("status", [])
                           if not (row["index"] == "?" and row["worktree"] == "?"
                                   and any(row["path"] == path or row["path"].startswith(path + "/") for path in caches))]
    return digest(value)


def freeze_product(repo: Path, snapshot: dict, destination: Path) -> dict:
    """Save source for independent before/after replay without copying auth files."""
    destination.mkdir(parents=True, mode=0o700)
    copied, omitted = [], [dict(row) for row in snapshot.get("skipped", [])]
    for row in snapshot["files"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe path in source snapshot")
        if not row.get("exists", True):
            continue
        name = relative.name.lower()
        sensitive = row.get("sensitive", False) or name == ".env" or name.startswith(".env.") or name.endswith((".pem", ".key", ".p12", ".pfx")) or name in {"id_rsa", "id_ed25519"}
        if sensitive:
            omitted.append({"path": relative.as_posix(), "reason": "sensitive-content-not-copied"})
            continue
        source, target = repo / relative, destination / relative
        if not source.parent.resolve().is_relative_to(repo):
            raise ValueError("source snapshot path traverses an external symlink")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            if not source.resolve().is_relative_to(repo):
                omitted.append({"path": relative.as_posix(), "reason": "external-symlink-not-copied"})
                continue
            link = os.readlink(source)
            if os.path.isabs(link):
                link = os.path.relpath(destination / source.resolve().relative_to(repo), target.parent)
            target.symlink_to(link)
        else:
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("source changed while freezing product: " + row["path"])
            target.write_bytes(data)
            target.chmod(source.stat().st_mode & 0o555 or 0o444)
        copied.append(relative.as_posix())
    return {"path": str(destination), "copied": copied, "omitted": omitted,
            "note": "Source replay snapshot; Git metadata, untracked conventional runtime caches, credentials, and external symlinks are omitted and reported. Rehydrate dependencies externally."}


def freeze_package(manifest: dict, destination: Path) -> dict:
    """Retain the exact public skill inputs for later diagnosis of changed runs."""
    from capture import _sanitize_text
    blobs = destination / "blobs"
    blobs.mkdir(parents=True, mode=0o700)
    saved, omitted = [], []
    for row in manifest["files"]:
        data = Path(row["resolved_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("selected skill changed while freezing inputs")
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            decoded = None
        if row.get("sensitive") or (decoded is not None and _sanitize_text(decoded) != decoded):
            omitted.append({"logical_path": row["logical_path"], "reason": "credential-shaped-input"})
            continue
        target = blobs / row["sha256"]
        if not target.exists():
            target.write_bytes(data)
            target.chmod(0o444)
        saved.append({"logical_path": row["logical_path"], "sha256": row["sha256"], "blob": str(target.relative_to(destination))})
    result = {"saved": saved, "omitted": omitted, "package_sha256": manifest["aggregate_sha256"]}
    write_json(destination / "index.json", result)
    return result


def harness_manifest(root: Path | None = None) -> dict:
    """Fingerprint the direct Python/JSON inputs used by this observer."""
    source_root = (root or OBSERVER_ROOT).resolve()
    files = []
    for path in sorted(source_root.iterdir()):
        if path.is_file() and path.suffix in {".py", ".json"}:
            files.append({"logical_path": path.name, "resolved_path": str(path.resolve()),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"root": str(source_root), "files": files,
            "aggregate_sha256": digest({row["logical_path"]: row["sha256"] for row in files})}


def manifest_delta(before: dict, after: dict) -> dict:
    """Describe observer-source drift without pretending it was a skill change."""
    old = {row["logical_path"]: row["sha256"] for row in before["files"]}
    new = {row["logical_path"]: row["sha256"] for row in after["files"]}
    return {"added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
            "changed": sorted(path for path in set(old) & set(new) if old[path] != new[path])}


def freeze_harness(destination: Path, manifest: dict | None = None) -> dict:
    """Retain the observer revision separately from the skill under test."""
    expected = manifest or harness_manifest()
    if harness_manifest(Path(expected["root"]))["aggregate_sha256"] != expected["aggregate_sha256"]:
        raise ValueError("observer-source-changed while freezing trial inputs")
    try:
        return freeze_package(expected, destination)
    except ValueError as exc:
        if str(exc) == "selected skill changed while freezing inputs":
            raise ValueError("observer-source-changed while freezing trial inputs") from exc
        raise


def scenarios() -> list[dict]:
    catalog = read_json(HERE / "scenarios.json")
    if catalog.get("schema_version") != 1:
        raise ValueError("unsupported scenario catalog")
    return catalog["scenarios"]


def find_step(step_id: str) -> dict:
    matches = [step for family in scenarios() for step in family["steps"] if step["id"] == step_id]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate step: {step_id}")
    return matches[0]


def resolve_git(selected: str | None) -> str:
    candidates = [selected] if selected else [shutil.which("git"), "/Library/Developer/CommandLineTools/usr/bin/git"]
    for value in candidates:
        if not value:
            continue
        path = shutil.which(value) or value
        try:
            result = subprocess.run([path, "--version"], capture_output=True, timeout=10, text=True)
            if result.returncode == 0:
                return str(Path(path).absolute())
        except (OSError, subprocess.TimeoutExpired):
            pass
    raise ValueError("a working Git executable is required; use --git without changing system settings")


def source_snapshot(repo: Path, git: str) -> dict:
    probe = subprocess.run([git, "-C", str(repo), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if probe.returncode == 0:
        if Path(probe.stdout.strip()).resolve() != repo.resolve():
            raise ValueError("product directory must be a repository root, not a nested directory of another repo")
        return repo_snapshot(repo, git)
    if any(repo.iterdir()):
        raise ValueError("non-Git product folder must be empty; existing products must have Git history")
    return {"repo": str(repo), "resolved_repo": str(repo.resolve()), "head": None,
            "status": [], "index": None, "files": [], "skipped": [], "new_empty_folder": True}


def _resolved_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _new_suite_product_parent(campaign_root: Path, observer_root: Path) -> Path:
    """Allocate a retained product parent outside the observer and campaign trees."""
    parent = Path(tempfile.mkdtemp(prefix="shiploop-e2e-products-")).resolve()
    if _paths_overlap(parent, campaign_root) or _paths_overlap(parent, observer_root):
        raise ValueError("temporary product parent must be outside campaign and observer roots")
    return parent


def _control_input_blocks(result: dict) -> bool:
    observation = result.get("control_input_observation")
    return bool(isinstance(observation, dict) and (
        observation.get("exposure_observed") or not observation.get("observation_complete")
    ))


def _unavailable_control_input_observation(reason: str) -> dict:
    return {
        "schema_version": _CONTROL_INPUT_OBSERVER_SCHEMA,
        "scope": "Structured stdout tool_call rawInput only; top-level observer argv and model text/output are excluded.",
        "controls": [],
        "references": [],
        "exposure_observed": False,
        "observation_complete": False,
        "status": "control-input-observation-unavailable",
        "error": reason,
        "limitations": [
            "A missing or malformed declared control-root contract cannot establish clean observation.",
            "Relative, encoded, or unreported accesses are outside this observation and are not claimed absent.",
        ],
    }


def _refresh_control_input_observation(output: Path, result: dict, manifest: dict) -> None:
    """Re-scan retained stdout before late grading without clearing an exposure."""
    roots = manifest.get("control_roots")
    previous = result.get("control_input_observation")
    contract = manifest.get("control_input_observer")
    declared_gate = contract is not None or "control_roots" in manifest or isinstance(previous, dict)
    if not declared_gate:
        # Pre-gate trials retain their historical compatibility behavior. New
        # manifests carry the versioned contract below and fail closed.
        return
    if not isinstance(contract, dict) or contract.get("schema_version") != _CONTROL_INPUT_OBSERVER_SCHEMA or contract.get("required") is not True:
        current = _unavailable_control_input_observation("declared control-input observer contract is malformed")
    elif not isinstance(roots, dict) or not roots:
        current = _unavailable_control_input_observation("declared control roots are missing or malformed")
    else:
        try:
            current = observe_control_input_references(output / "capture" / "events.jsonl", roots)
        except (OSError, ValueError, RuntimeError) as exc:
            current = _unavailable_control_input_observation(
                f"declared control-root observation failed: {exc.__class__.__name__}"
            )
    if isinstance(previous, dict) and previous.get("exposure_observed") and not current.get("exposure_observed"):
        preserved = dict(previous)
        preserved["late_recomputation"] = {
            "status": current.get("status"),
            "observation_complete": current.get("observation_complete"),
        }
        current = preserved
    result["control_input_observation"] = current
    result.setdefault("statuses", {})["control_input"] = current.get("status", "control-input-observation-unavailable")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _refresh_late_grade_observer_identity(output: Path, result: dict, manifest: dict) -> None:
    """Recheck the trusted observer root before a late grade.

    New trials bind the frozen identity in both manifest and result. Truly
    legacy receipts without any observer binding keep their historical grading
    behavior; no editable trial path is used to select the current observer.
    """
    previous_stable = result.get("observer_stable")
    manifest_contract = manifest.get("observer_late_grade_contract")
    result_contract = result.get("observer_late_grade_contract")
    modern_contract = "observer_late_grade_contract" in manifest or "observer_late_grade_contract" in result
    bound_legacy = (
        "observer_sha256" in manifest
        or "observer_digest" in result
        or isinstance(result.get("harness_snapshot"), dict)
        or (output / "harness-inputs" / "index.json").is_file()
    )
    observation: dict[str, Any] = {
        "schema_version": _OBSERVER_LATE_GRADE_SCHEMA,
        "trusted_observer_root": str(Path(OBSERVER_ROOT).resolve()),
        "previous_observer_stable": previous_stable,
    }

    def invalidate(reason: str) -> None:
        observation.update(
            identity_complete=False,
            matches_frozen_identity=False,
            status="observer-identity-unavailable",
            reason=reason,
        )
        result["late_grade_observer_observation"] = observation
        result["observer_stable"] = False
        if previous_stable is not False:
            result.setdefault("statuses", {})["observer"] = "observer-identity-unavailable"

    if not modern_contract and not bound_legacy:
        observation.update(
            identity_complete=False,
            matches_frozen_identity=None,
            status="legacy-observer-identity-not-declared",
            policy="No current observer is selected from editable legacy trial artifacts.",
        )
        result["late_grade_observer_observation"] = observation
        return

    if modern_contract:
        if not isinstance(manifest_contract, dict) or not isinstance(result_contract, dict):
            invalidate("new trial is missing a manifest/result observer contract")
            return
        if manifest_contract.get("schema_version") != _OBSERVER_LATE_GRADE_SCHEMA or result_contract.get("schema_version") != _OBSERVER_LATE_GRADE_SCHEMA:
            invalidate("new trial observer contract has an unsupported schema")
            return
        expected = manifest_contract.get("frozen_sha256")
        if result_contract.get("frozen_sha256") != expected:
            invalidate("manifest and result frozen observer identities disagree")
            return
    else:
        # Earlier observer-bound receipts used observer_sha256 directly. They
        # remain checkable, but an unbound receipt is never retroactively rooted
        # through editable trial metadata.
        expected = manifest.get("observer_sha256")
        observation["legacy_bound_identity"] = True

    if not _is_sha256(expected):
        invalidate("frozen observer identity is missing or malformed")
        return
    if manifest.get("observer_sha256") != expected or manifest.get("harness_sha256") != expected:
        invalidate("manifest observer identity does not match its frozen binding")
        return
    if result.get("observer_digest") != expected:
        invalidate("result observer identity does not match its frozen binding")
        return
    snapshot = result.get("harness_snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("package_sha256") != expected:
        invalidate("result frozen observer snapshot is missing or inconsistent")
        return
    try:
        frozen_snapshot = read_json(output / "harness-inputs" / "index.json")
    except (OSError, ValueError, TypeError) as exc:
        invalidate(f"frozen observer snapshot is unavailable: {exc.__class__.__name__}")
        return
    if not isinstance(frozen_snapshot, dict) or frozen_snapshot.get("package_sha256") != expected:
        invalidate("retained frozen observer snapshot is missing or inconsistent")
        return
    try:
        # Intentionally use the process-owned root, never a root stored in the
        # editable manifest, result, or provenance artifact.
        current = harness_manifest()
    except (OSError, ValueError, TypeError) as exc:
        invalidate(f"trusted observer identity could not be recomputed: {exc.__class__.__name__}")
        return

    matched = current["aggregate_sha256"] == expected
    observation.update(
        identity_complete=True,
        frozen_sha256=expected,
        frozen_snapshot_sha256=frozen_snapshot["package_sha256"],
        current=current,
        matches_frozen_identity=matched,
        status="matched-frozen-observer" if matched else "observer-drift-observed",
    )
    result["late_grade_observer_observation"] = observation
    if previous_stable is False:
        observation["status"] = "prior-invalidity-preserved"
        return
    if matched:
        result["observer_stable"] = True
    else:
        result["observer_stable"] = False
        result.setdefault("statuses", {})["observer"] = "changed-after-trial-invalid"


def preflight(args: argparse.Namespace, repo: Path, env: dict) -> dict:
    expected = Path(args.skill_root).expanduser().absolute()
    package = package_manifest(expected)
    selection = inspect_selection(args.grok, repo, expected, env)
    version = subprocess.run([args.grok, "--version"], cwd=repo, env=env,
                             capture_output=True, text=True, timeout=30)
    if version.returncode != 0:
        raise ValueError("Grok --version failed")
    return {"package": package, "selection": selection,
            "grok_version": version.stdout.strip(), "model_requested": args.model,
            "python": sys.version.split()[0]}


def report(output: Path, result: dict) -> None:
    write_json(output / "result.json", result)
    statuses = result.get("statuses", {})
    lines = ["# ShipLoop one-shot trial", "", f"Trial: `{result['trial_id']}`", "",
             "| Dimension | Observation |", "| --- | --- |"]
    lines.extend(f"| {key} | {str(value).replace('|', '/')} |" for key, value in statuses.items())
    lines.extend(["", "This report separates observations from independent verification. "
                  "A Grok exit code or ShipLoop completion declaration cannot establish product correctness.", "",
                  "See `manifest.json`, `capture/stdout.log`, `capture/stderr.log`, "
                  "`capture/events.jsonl`, `before.json`, `after.json`, and `artifacts/`.", ""])
    if result.get("error"):
        lines.extend(["Recorded error: " + result["error"], ""])
    if result.get("audit"):
        audit = result["audit"]
        native = audit["native_events"]
        lines.extend(["Observed performance:", "",
                      f"- Elapsed: {audit['process']['wall_duration_seconds']} seconds.",
                      f"- Tool calls: {native['tool_call_count']}; observed failed tools: {native['tool_failed_count']}.",
                      f"- Reported usage: `{json.dumps(audit['usage']['reported_terminal_usage'])}` (null means unavailable).", ""])
        for row in audit["runs"]:
            if not row.get("preexisting"):
                lines.append(f"Run `{row['run_id']}`: {row['work_items_planned']} planned work items, "
                             f"{row['work_items_completed']} declared completed; "
                             f"{row['repeat_count']} repeat and {row['blocked_count']} blocked callbacks.")
        lines.extend(["", "`audit.json` retains per-stage accepted counts and observed tool timing; "
                      "it does not infer Improve iteration counts or missing token/cost usage.", ""])
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def read_baseline(args: argparse.Namespace, step: dict, before: dict) -> dict | None:
    if not step.get("depends_on"):
        if args.baseline:
            raise ValueError("a create scenario does not accept --baseline")
        if not before.get("new_empty_folder") or before.get("files") or before.get("head"):
            raise ValueError("create scenario requires a new empty product folder; leave Git bootstrap to ShipLoop")
        return None
    if not args.baseline:
        raise ValueError("feature/refinement requires --baseline pointing to its predecessor result.json")
    baseline_path = Path(args.baseline).expanduser().resolve()
    if baseline_path.name != "result.json":
        raise ValueError("baseline must be the canonical result.json in a retained trial directory")
    baseline = read_json(baseline_path)
    if baseline.get("step_id") != step["depends_on"]:
        raise ValueError("baseline is not the declared predecessor scenario")
    if baseline.get("repo") != before["resolved_repo"]:
        raise ValueError("feature must use the same original product repository")
    if baseline.get("candidate_digest") != candidate_digest(before):
        raise ValueError("product changed after predecessor grading; freeze/reverify that baseline first")
    if baseline.get("statuses", {}).get("overall") != "passed" and not args.diagnostic_unverified_baseline:
        raise ValueError("predecessor is not independently verified; grade it or explicitly use --diagnostic-unverified-baseline")
    previous_root = baseline_path.parent
    previous_manifest = read_json(previous_root / "manifest.json")
    previous_snapshot = read_json(previous_root / "after.json")
    if (previous_manifest.get("trial_id") != baseline.get("trial_id")
            or previous_manifest.get("scenario", {}).get("id") != baseline.get("step_id")
            or candidate_digest(previous_snapshot) != baseline.get("candidate_digest")):
        raise ValueError("predecessor manifest/snapshot binding is inconsistent")
    if not args.diagnostic_unverified_baseline:
        previous_receipt = read_json(previous_root / "verification.json")
        checked = validate_receipt(previous_receipt, trial_id=baseline["trial_id"],
                                   candidate_digest=baseline["candidate_digest"],
                                   required_checks=previous_manifest["scenario"]["required_checks"],
                                   evidence_root=previous_root / "verification",
                                   baseline_digest=baseline.get("baseline_digest"))
        if checked != read_json(previous_root / "grade.json") or not full_pass_eligible(baseline, checked):
            raise ValueError("predecessor independent evidence does not support a passing baseline")
    return baseline


def run_trial(args: argparse.Namespace) -> int:
    step = find_step(args.step)
    stop_stage = getattr(args, "stop_after_stage", None)
    requested_repo = Path(args.repo).expanduser().absolute()
    requested_output = Path(args.output).expanduser().absolute()
    repo = requested_repo.resolve()
    output = requested_output.resolve()
    if output.exists():
        raise ValueError("--output must be a new directory; prior attempts are never overwritten")
    if _paths_overlap(output, repo):
        raise ValueError("product and trial output must be separate, non-nested directories")
    if not repo.exists():
        if step["kind"] != "create":
            raise ValueError("existing feature repository does not exist")
        repo.mkdir(parents=True)
    if requested_repo.is_symlink():
        raise ValueError("use the product's real path, not a symlink")
    output.mkdir(parents=True, mode=0o700)
    trial_id = output.name
    result: dict = {"schema_version": 1, "trial_id": trial_id, "step_id": step["id"],
                    "partial": bool(stop_stage), "stop_after_stage": stop_stage,
                    "repo": str(repo), "statuses": {"overall": "incomplete", "product": "unverified"},
                    "required_checks": step["required_checks"],
                    "requires_incremental_review": step.get("requires_incremental_review", step["kind"] != "create")}
    report(output, result)
    try:
        observer_entry = harness_manifest()
        observer_provenance = {
            "schema_version": 1,
            "scope": "Detects observer Python/JSON source drift from trial entry through final observation; it does not authenticate module bytes loaded before trial entry.",
            "entry": observer_entry,
            "phases": {},
        }
        result["observer_digest"] = observer_entry["aggregate_sha256"]
        result["observer_root"] = observer_entry["root"]
        result["observer_provenance"] = "observer-provenance.json"
        result["statuses"]["observer"] = "frozen-awaiting-observation"
        write_json(output / "observer-provenance.json", observer_provenance)
        try:
            result["harness_snapshot"] = freeze_harness(output / "harness-inputs", observer_entry)
        except ValueError as exc:
            current = harness_manifest(Path(observer_entry["root"]))
            observer_provenance["freeze_failure"] = {"manifest": current,
                                                       "matches_entry": False,
                                                       "delta_from_entry": manifest_delta(observer_entry, current)}
            write_json(output / "observer-provenance.json", observer_provenance)
            result["observer_stable"] = False
            result["statuses"]["observer"] = "source-changed-before-launch"
            raise ValueError("observer-source-changed while freezing trial inputs; no model was launched") from exc

        frozen_observer_sha = result["harness_snapshot"]["package_sha256"]
        result["observer_late_grade_contract"] = {
            "schema_version": _OBSERVER_LATE_GRADE_SCHEMA,
            "frozen_sha256": frozen_observer_sha,
        }
        observer_provenance["frozen_snapshot"] = {"package_sha256": frozen_observer_sha,
                                                    "matches_entry": frozen_observer_sha == observer_entry["aggregate_sha256"]}
        write_json(output / "observer-provenance.json", observer_provenance)

        def record_observer_phase(phase: str) -> tuple[dict, bool]:
            current = harness_manifest(Path(observer_entry["root"]))
            matches_entry = current["aggregate_sha256"] == observer_entry["aggregate_sha256"]
            matches_frozen = current["aggregate_sha256"] == frozen_observer_sha
            observer_provenance["phases"][phase] = {"manifest": current,
                                                      "matches_entry": matches_entry,
                                                      "matches_frozen_snapshot": matches_frozen,
                                                      "delta_from_entry": manifest_delta(observer_entry, current)}
            write_json(output / "observer-provenance.json", observer_provenance)
            return current, matches_entry and matches_frozen

        git = resolve_git(args.git)
        env = dict(os.environ)
        # Process-scoped only. Inherit auth through the normal host; never copy it into artifacts.
        env.update(PATH=str(Path(git).parent) + os.pathsep + env.get("PATH", ""),
                   GIT_TERMINAL_PROMPT="0", GROK_MEMORY="0", NO_COLOR="1")
        # Grok's login shell may rebuild PATH. Keep Apple's /usr/bin/git using
        # the already-probed CLT toolchain in that shell as well (no system edit).
        developer_dir = None
        if Path(git).is_relative_to("/Library/Developer/CommandLineTools/"):
            developer_dir = "/Library/Developer/CommandLineTools"
            env["DEVELOPER_DIR"] = developer_dir
        before = source_snapshot(repo, git)
        write_json(output / "before.json", before)
        baseline = read_baseline(args, step, before)
        result["product_before"] = freeze_product(repo, before, output / "product-before")
        result["baseline_digest"] = candidate_digest(before) if baseline else None
        result["diagnostic"] = bool(args.diagnostic_unverified_baseline)
        info = preflight(args, repo, env)
        _, observer_after_preflight = record_observer_phase("after_preflight")
        if not observer_after_preflight:
            result["observer_stable"] = False
            result["statuses"]["observer"] = "source-changed-before-launch"
            raise ValueError("observer-source-changed before model launch; no model was launched")
        result["package_snapshot"] = freeze_package(info["package"], output / "package-inputs")
        prompt = step["prompt"]
        (output / "prompt.txt").write_text(prompt, encoding="utf-8")
        selected_cli = Path(args.skill_root).expanduser() / "scripts" / "shiploop"
        control_roots = {
            "trial_output": str(output.resolve()),
            "observer_source": str(Path(observer_entry["root"]).resolve()),
        }
        campaign_control = getattr(args, "control_root", None)
        if campaign_control:
            control_roots["campaign_control"] = str(_resolved_path(campaign_control))
        argv = build_argv(args.grok, output / "prompt.txt", repo, args.model,
                          args.max_turns, args.permission_mode, args.reasoning_effort)
        roots = [repo, repo.parent / ".shiploop-runs", repo.parent.parent / ".shiploop-runs"]
        roots.extend(Path(value).expanduser().resolve() for value in args.artifact_root)
        for root in roots:
            if root.resolve() == output.resolve() or output.resolve().is_relative_to(root.resolve()):
                raise ValueError("artifact scan roots must not contain trial output")
        manifest = {"schema_version": 1, "trial_id": trial_id, "scenario": step,
                    "harness_sha256": result["harness_snapshot"]["package_sha256"],
                    "observer_sha256": observer_entry["aggregate_sha256"],
                    "observer_late_grade_contract": result["observer_late_grade_contract"],
                    "observer_provenance": result["observer_provenance"],
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "repo": str(repo), "launch_cwd": str(repo), "output": str(output), "argv": argv, "preflight": info,
                    "git": git, "timeout_seconds": args.timeout, "max_turns": args.max_turns,
                    "stop_after_stage": stop_stage, "partial": bool(stop_stage),
                    "permission_mode": args.permission_mode, "reasoning_effort_requested": args.reasoning_effort, "memory": "disabled",
                    "developer_dir_override": developer_dir,
                    "capture_limits": {"max_log_bytes": args.max_log_bytes, "max_event_line_chars": args.max_event_line_chars},
                    "artifact_roots": [str(root) for root in roots],
                    "control_input_observer": {"schema_version": _CONTROL_INPUT_OBSERVER_SCHEMA, "required": True},
                    "control_roots": control_roots,
                    "selected_cli": str(selected_cli),
                    "baseline_result": str(Path(args.baseline).resolve()) if args.baseline else None,
                    "diagnostic_unverified_baseline": bool(args.diagnostic_unverified_baseline)}
        write_json(output / "manifest.json", manifest)
        if candidate_digest(source_snapshot(repo, git)) != candidate_digest(before):
            raise ValueError("product changed during preflight; no model was launched")
        initial = capture_run_artifacts(roots, output / "initial-evidence")
        write_json(output / "initial-evidence.json", initial)
        last_snapshot = 0.0
        last_capture: dict = {}

        def observe() -> None:
            nonlocal last_snapshot, last_capture
            if time.monotonic() - last_snapshot >= 2:
                last_capture = capture_run_artifacts(roots, output / "artifacts")
                last_snapshot = time.monotonic()

        boundary_seen: dict = {}
        boundary_snapshot = -1.0

        def reached_boundary() -> bool:
            nonlocal boundary_seen, boundary_snapshot
            if not stop_stage or not last_capture or boundary_snapshot == last_snapshot:
                return False
            boundary_snapshot = last_snapshot
            nav = inspect_run_artifacts(last_capture)
            host = summarize_events(output / "capture/events.jsonl", selected_cli)
            boundary_seen = partial_observation(nav, host, prompt, repo, initial, last_capture, stop_stage)
            # Stop at durable acceptance even if telemetry is incomplete. Final
            # grading still requires callback correlation; an observer gap must
            # not cause the model to keep building beyond the requested prefix.
            return boundary_seen.get("durable_boundary_reached", False)

        _, observer_at_launch = record_observer_phase("before_model_launch")
        if not observer_at_launch:
            result["observer_stable"] = False
            result["statuses"]["observer"] = "source-changed-before-launch"
            raise ValueError("observer-source-changed before model launch; no model was launched")
        process = capture_process(argv, repo, output / "capture", args.timeout, env=env, on_tick=observe,
                                  should_stop=reached_boundary if stop_stage else None,
                                  max_log_bytes=args.max_log_bytes, max_event_line_chars=args.max_event_line_chars)
        result["process"] = process
        last_capture = capture_run_artifacts(roots, output / "artifacts")
        write_json(output / "artifact-index.json", last_capture)
        navigation = inspect_run_artifacts(last_capture)
        write_json(output / "navigation.json", navigation)
        result["navigation"] = navigation
        after = source_snapshot(repo, git)
        write_json(output / "after.json", after)
        result["product_after"] = freeze_product(repo, after, output / "product-after")
        result["candidate_digest"] = candidate_digest(after)
        result["change"] = compare_repos(before, after, repo, git)
        write_json(output / "change.json", result["change"])
        refreshed = preflight(args, repo, env)
        write_json(output / "preflight-after.json", refreshed)
        stable = info["package"]["aggregate_sha256"] == refreshed["package"]["aggregate_sha256"]
        result["skill_digest"] = info["package"]["aggregate_sha256"]
        result["skill_stable"] = stable
        events = summarize_events(output / "capture" / "events.jsonl", selected_cli)
        write_json(output / "host-observations.json", events)
        result["host_observations"] = events
        result["control_input_observation"] = observe_control_input_references(
            output / "capture" / "events.jsonl", control_roots,
        )
        result["statuses"]["control_input"] = result["control_input_observation"]["status"]
        result["isolation"] = assess_isolation(inspect_run_artifacts(initial), navigation, events, prompt=prompt)
        write_json(output / "recovery-isolation.json", result["isolation"])
        result["statuses"]["isolation"] = result["isolation"]["status"]
        audit = summarize_trial(process, navigation, output / "capture" / "events.jsonl")
        old_ids = {row["state"].get("run_id") for row in inspect_run_artifacts(initial)["states"] if isinstance(row.get("state"), dict)}
        for row in audit["runs"]:
            row["preexisting"] = row["run_id"] in old_ids
        write_json(output / "audit.json", audit)
        result["audit"] = audit
        observer_after_observation, observer_stable = record_observer_phase("after_observation")
        result["observer_after_digest"] = observer_after_observation["aggregate_sha256"]
        result["observer_stable"] = observer_stable
        result["statuses"].update(process="exited" if process.get("exit_code") == 0 else "failed-or-budget-exhausted",
                                  skill="selected-stable" if stable else "changed-during-run-invalid",
                                  observer="stable" if observer_stable else "changed-during-observation-invalid",
                                  protocol="unverified", incrementality="unverified" if baseline else "not-applicable")
        # A current, matching terminal state and return receipt are assessed separately below.
        result["statuses"]["protocol"] = protocol_status(navigation, prompt, repo, initial, last_capture, after)
        result["lifecycle"] = lifecycle_observation(events, navigation, prompt, repo, initial)
        result["statuses"]["lifecycle"] = "observed" if result["lifecycle"]["complete"] else "unverified"
        result["statuses"]["overall"] = "awaiting-independent-verification"
        if not stable or not observer_stable or process.get("capture_error") or _control_input_blocks(result):
            result["statuses"]["overall"] = "invalid-trial"
        elif process.get("timed_out") or process.get("exit_code") != 0:
            result["statuses"]["overall"] = "incomplete"
        elif result["isolation"]["status"] == "fail":
            result["statuses"]["overall"] = "run-isolation-failed"
        if stop_stage:
            result["partial_observation"] = partial_observation(navigation, events, prompt, repo, initial, last_capture, stop_stage)
            result["boundary_at_stop"] = boundary_seen
            result["statuses"]["partial"] = "passed" if partial_pass_eligible(result) else "failed"
            if not stable or not observer_stable or process.get("capture_error") or _control_input_blocks(result):
                result["statuses"]["overall"] = "invalid-trial"
            elif result["isolation"]["status"] == "fail":
                result["statuses"]["overall"] = "run-isolation-failed"
            elif result["partial_observation"].get("accepted_after_boundary", 0) > 0:
                result["statuses"]["overall"] = "partial-smoke-overshot"
            else:
                result["statuses"]["overall"] = "partial-smoke-passed" if partial_pass_eligible(result) else "partial-smoke-failed"
            if process.get("termination_reason") == "requested_boundary":
                result["statuses"]["process"] = "stopped-at-observed-boundary"
        write_template(output / "verification-template.json", trial_id=trial_id,
                       candidate_digest=result["candidate_digest"], required_checks=step["required_checks"],
                       baseline_digest=result["baseline_digest"])
        report(output, result)
        if args.verifier and observer_stable and not _control_input_blocks(result):
            run_verifier(args, output, result, repo, env)
            _, observer_stable = record_observer_phase("after_verifier")
            result["observer_stable"] = observer_stable
            if not observer_stable:
                result["statuses"]["observer"] = "changed-during-observation-invalid"
                result["statuses"]["overall"] = "invalid-trial"
        report(output, result)
        return 0 if result["statuses"]["overall"] in {"passed", "partial-smoke-passed"} else 2
    except KeyboardInterrupt:
        result["error"] = "operator interrupted the trial; inspect retained process and workspace evidence before recovery"
        result["statuses"]["overall"] = "interrupted"
        report(output, result)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
        result["statuses"]["overall"] = "invalid-trial" if (
            result.get("observer_stable") is False or _control_input_blocks(result)
        ) else "harness-or-environment-error"
        report(output, result)
        return 2
    finally:
        # Derived, sanitized behavior is retained even for interrupted/incomplete
        # attempts. It does not submit callbacks or change the live verdict.
        try:
            write_trial_behavior(output)
        except Exception as exc:
            try:
                write_json(output / "behavior.json", {
                    "schema": "shiploop-e2e-live-behavior/1",
                    "capture_status": "unavailable",
                    "error_type": type(exc).__name__,
                    "limitations": ["Behavior export failed; inspect original retained trial evidence."],
                })
            except OSError:
                print("shiploop-e2e: behavior export unavailable; original trial outcome unchanged", file=sys.stderr)


def partial_observation(navigation: dict, events: dict, prompt: str, repo: Path,
                        initial: dict, captured: dict, stop_stage: str) -> dict:
    """Require accepted prefix results AND observed real callbacks; never advance state."""
    old_ids = {row["state"].get("run_id") for row in inspect_run_artifacts(initial)["states"]
               if isinstance(row.get("state"), dict)}
    matches = [row for row in navigation.get("states", []) if isinstance(row.get("state"), dict)
               and row["state"].get("prompt") in {prompt, prompt.removeprefix("/shiploop ")}
               and row["state"].get("run_id") not in old_ids]
    result = {"reached": False, "requested_stage": stop_stage,
              "scope": "Observed SDLC prefix only; product behavior and delivery remain unverified."}
    if len(matches) != 1:
        return {**result, "reason": "new-run-identity-unverified"}
    row = matches[0]
    state = row["state"]
    protocol_version = state.get("navigator_protocol_version")
    boundary = _partial_boundary(protocol_version, stop_stage)
    if boundary is None:
        return {**result, "reason": "unsupported-stop-stage-for-protocol"}
    target_stage, required_stages = boundary
    run_dir = Path(row["source_path"]).parent
    history = state.get("history", [])
    targets = [i for i, item in enumerate(history) if item.get("stage") == target_stage and item.get("outcome") == "done"]
    result.update(protocol_version=protocol_version, effective_stop_stage=target_stage,
                  required_stages=list(required_stages), run_id=state.get("run_id"),
                  current_stage=state.get("stage"), status=state.get("status"),
                  accepted_stages=[item.get("stage") for item in history])
    if not targets:
        return {**result, "reason": "requested-stage-not-accepted"}
    prefix = history[:targets[0] + 1]
    result["accepted_after_boundary"] = len(history) - len(prefix)
    # V2 records explicit review stages; v3 records each producer only after its
    # standalone Improve child completes. ``required_stages`` is protocol-local.
    completed = {item.get("stage") for item in prefix if item.get("outcome") == "done"}
    if not set(required_stages) <= completed:
        return {**result, "reason": "prefix-stage-gap"}
    accepted = state.get("accepted", {})
    results = {item["source_path"] for item in captured.get("artifacts", []) if item.get("kind") == "result"}
    if any(item.get("action") not in accepted or str(run_dir / "results" / (str(item.get("action")) + ".md")) not in results
           for item in prefix):
        return {**result, "reason": "missing-accepted-prefix-result"}
    if state.get("execution_mode") == "navigator-worktree":
        bindings = [item.get("workspace", {}) for item in navigation.get("workspaces", [])
                    if item.get("workspace", {}).get("run_dir") == str(run_dir)]
        if len(bindings) != 1 or bindings[0].get("source_repo") != str(repo) or bindings[0].get("worktree") != state.get("repo"):
            return {**result, "reason": "workspace-binding-unverified"}
    elif state.get("repo") != str(repo):
        return {**result, "reason": "direct-repository-binding-unverified"}
    result["durable_boundary_reached"] = True
    prefix_navigation = {**navigation, "states": [{**row, "state": {**state, "history": prefix}}]}
    lifecycle = lifecycle_observation(events, prefix_navigation, prompt, repo, initial)
    result["prefix_lifecycle"] = lifecycle
    result["reached"] = bool(lifecycle.get("start_observed") and not lifecycle.get("missing_callback_actions"))
    result["reason"] = "accepted-prefix-and-callbacks-observed" if result["reached"] else "prefix-callbacks-unverified"
    return result


def partial_pass_eligible(result: dict) -> bool:
    process = result.get("process", {})
    return bool(result.get("partial") and result.get("partial_observation", {}).get("reached")
                and result.get("partial_observation", {}).get("accepted_after_boundary") == 0
                and result.get("skill_stable") and result.get("observer_stable") is not False
                and result.get("isolation", {}).get("status") in (None, "pass")
                and not _control_input_blocks(result)
                and not result.get("diagnostic")
                and not process.get("timed_out") and not process.get("capture_error") and not process.get("truncated")
                and process.get("termination_reason") == "requested_boundary"
                and not result.get("host_observations", {}).get("terminal", {}).get("error_observed"))


def protocol_status(navigation: dict, prompt: str, repo: Path, initial: dict,
                    final_capture: dict, after: dict) -> str:
    """Correlate new-run identity and guarded return; these remain declarations."""
    prior_ids = {row["state"].get("run_id") for row in inspect_run_artifacts(initial)["states"] if isinstance(row.get("state"), dict)}
    documents = navigation.get("states", [])
    matches = []
    for document in documents:
        state = document.get("state") or {}
        # The router may remove the slash-command token. No paraphrase is accepted.
        if state.get("prompt") in {prompt, prompt.removeprefix("/shiploop ")} and state.get("run_id") not in prior_ids:
            matches.append(document)
    if not matches:
        return "unverified-no-new-matching-state"
    if len(matches) != 1:
        return "unverified-multiple-matching-runs"
    latest = matches[0]
    state = latest["state"]
    if state.get("status") != "done":
        return "incomplete-" + str(state.get("status", "unknown"))
    action = state.get("action")
    # Protocol 2 retains the terminal ROOT action; completed INNER items use null.
    if (not state.get("run_id") or state.get("stage") != "done"
            or not isinstance(action, dict) or action.get("stage") != "done" or not action.get("id")):
        return "unverified-inconsistent-terminal-state"
    run_dir = Path(latest["source_path"]).parent
    if not any(row["source_path"] == str(run_dir / "report.html") for row in final_capture["artifacts"]):
        return "unverified-missing-terminal-report"
    history, accepted = state.get("history"), state.get("accepted")
    if not isinstance(history, list) or not history or not isinstance(accepted, dict):
        return "unverified-missing-accepted-history"
    observed_results = {row["source_path"] for row in final_capture["artifacts"] if row["kind"] == "result"}
    for entry in history:
        if not isinstance(entry, dict) or entry.get("action") not in accepted:
            return "unverified-history-result-mismatch"
        if str(run_dir / "results" / (str(entry["action"]) + ".md")) not in observed_results:
            return "unverified-missing-accepted-result"
    if state.get("execution_mode") != "navigator-worktree":
        return "declared-complete-direct-mode-review-required"
    workspaces = [row for row in navigation.get("workspaces", [])
                  if (row.get("workspace") or {}).get("run_dir") == str(run_dir)]
    if len(workspaces) != 1:
        return "unverified-workspace-binding"
    workspace_row = workspaces[0]
    workspace = workspace_row["workspace"]
    if (workspace.get("source_repo") != str(repo) or workspace.get("worktree") != state.get("repo")
            or workspace.get("status") != "returned"):
        return "unverified-workspace-return-identity"
    receipt_path = Path(workspace_row["source_path"]).parent / "return-receipt.md"
    receipts = [row.get("receipt") for row in navigation.get("guarded_receipt_presence", {}).get("receipts", [])
                if row["source_path"] == str(receipt_path)]
    if len(receipts) != 1 or not isinstance(receipts[0], dict) or receipts[0].get("status") != "returned":
        return "unverified-missing-return-receipt"
    expected = receipts[0].get("expected_source", {})
    if expected.get("head") and expected["head"] != after.get("head"):
        return "unverified-return-source-head"
    return "declared-complete-return-observed"


def lifecycle_observation(events: dict, navigation: dict, prompt: str, repo: Path, initial: dict) -> dict:
    """Bind captured selected-CLI commands to every accepted action of this run."""
    old_ids = {row["state"].get("run_id") for row in inspect_run_artifacts(initial)["states"] if isinstance(row.get("state"), dict)}
    matches = [row for row in navigation.get("states", []) if isinstance(row.get("state"), dict)
               and row["state"].get("prompt") in {prompt, prompt.removeprefix("/shiploop ")}
               and row["state"].get("run_id") not in old_ids]
    if len(matches) != 1:
        return {"complete": False, "reason": "new-run-identity-unverified"}
    record = matches[0]
    run_dir = Path(record["source_path"]).parent.resolve()
    workspace_root = run_dir.parent
    state = record["state"]
    protocol_version = state.get("navigator_protocol_version")
    required_actions = {entry["action"] for entry in state.get("history", []) if isinstance(entry, dict) and isinstance(entry.get("action"), str)}
    callback_commands = {"improve-complete"} if protocol_version == 3 else {"complete", "done"}
    callbacks: set[str] = set()
    started = returned = False
    call_counts = Counter(call.get("call_id") for call in events.get("cli_calls", []))
    ambiguous_ids = sorted(str(call_id) for call_id, count in call_counts.items() if count != 1)

    def same_path(value: str | None, expected: Path) -> bool:
        return isinstance(value, str) and Path(value).is_absolute() and Path(value).resolve() == expected.resolve()

    for call in events.get("cli_calls", []):
        if (call_counts[call.get("call_id")] != 1 or not call.get("completed") or call.get("failed")
                or not call.get("exit_codes")
                or any(code != 0 for code in call.get("exit_codes", []))):
            continue
        tail = call.get("argv_tail", [])
        flags: dict[str, str] = {}
        for index, token in enumerate(tail):
            if token.startswith("--"):
                key, equal, value = token.partition("=")
                if not equal and index + 1 < len(tail):
                    value = tail[index + 1]
                flags[key] = value
        if tail[:2] == ["workspace", "start"] and same_path(flags.get("--repo"), repo) and same_path(flags.get("--workspace-root"), workspace_root):
            started = True
        if tail[:1] == ["init"] and same_path(flags.get("--repo"), repo) and same_path(flags.get("--run-dir"), run_dir):
            started = True
        if tail[:1] and tail[0] in callback_commands and same_path(flags.get("--run-dir"), run_dir) and flags.get("--action") in required_actions:
            callbacks.add(flags["--action"])
        if tail[:2] == ["workspace", "return"] and same_path(flags.get("--workspace-root"), workspace_root):
            returned = True
    missing = sorted(required_actions - callbacks)
    needs_return = state.get("execution_mode") == "navigator-worktree"
    return {"complete": started and bool(required_actions) and not missing and (returned or not needs_return),
            "run_id": state["run_id"], "protocol_version": protocol_version,
            "callback_commands": sorted(callback_commands), "start_observed": started,
            "return_observed": returned, "accepted_action_count": len(required_actions),
            "observed_callback_count": len(callbacks), "missing_callback_actions": missing,
            "ambiguous_tool_call_ids": ambiguous_ids,
            "note": "Commands are correlated with host tool completion and declared state; unknown exit codes remain unknown."}


def run_verifier(args: argparse.Namespace, output: Path, result: dict, repo: Path, env: dict) -> None:
    argv = json.loads(args.verifier)
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("--verifier must be a JSON argv array, not a shell command")
    evidence_dir = output / "verification"
    evidence_dir.mkdir(exist_ok=True)
    verifier_env = dict(env)
    verifier_env.update(SHIPLOOP_E2E_TRIAL=str(output), SHIPLOOP_E2E_REPO=str(repo),
                        SHIPLOOP_E2E_EVIDENCE=str(evidence_dir), SHIPLOOP_E2E_BASELINE=str(output / "product-before"))
    observed = capture_process(argv, evidence_dir, output / "verifier-capture", args.verifier_timeout, env=verifier_env)
    write_json(output / "verifier-process.json", observed)
    if observed.get("exit_code") != 0 or observed.get("timed_out"):
        result["statuses"]["product"] = "verifier-failed"
        return
    receipt = read_json(output / "verifier-capture" / "stdout.log")
    write_json(output / "verification.json", receipt)
    apply_grade(output, result, receipt)


def apply_grade(output: Path, result: dict, receipt: dict) -> None:
    manifest = read_json(output / "manifest.json")
    _refresh_control_input_observation(output, result, manifest)
    _refresh_late_grade_observer_identity(output, result, manifest)
    if manifest.get("partial") or result.get("partial"):
        raise ValueError("partial smoke trials cannot be graded as full product E2E passes")
    if (result["trial_id"] != manifest["trial_id"]
            or result["step_id"] != manifest["scenario"]["id"]
            or result["required_checks"] != manifest["scenario"]["required_checks"]
            or result["requires_incremental_review"] != manifest["scenario"]["requires_incremental_review"]
            or result["candidate_digest"] != candidate_digest(read_json(output / "after.json"))):
        raise ValueError("trial result no longer matches its frozen scenario and source snapshot")
    current = source_snapshot(Path(result["repo"]), manifest["git"])
    if candidate_digest(current) != result["candidate_digest"]:
        raise ValueError("verification changed the product or graded a stale candidate")
    grade = validate_receipt(receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                             required_checks=result["required_checks"], evidence_root=output / "verification",
                             baseline_digest=result.get("baseline_digest"))
    write_json(output / "grade.json", grade)
    result["grade"] = grade
    result["statuses"]["product"] = grade.get("product_status", "unverified")
    result["statuses"]["incrementality"] = grade.get("incremental_status", "unverified") if result["requires_incremental_review"] else "not-applicable"
    # Regrading a formerly passing candidate must never retain a stale overall pass.
    result["statuses"]["overall"] = "awaiting-independent-verification"
    invalid_trial = (
        not grade.get("receipt_valid")
        or not result.get("skill_stable")
        or result.get("observer_stable") is False
        or result.get("process", {}).get("capture_error")
    )
    if invalid_trial:
        result["statuses"]["overall"] = "invalid-trial"
    elif result.get("process", {}).get("timed_out") or result.get("process", {}).get("exit_code") != 0:
        result["statuses"]["overall"] = "incomplete"
    if not invalid_trial and full_pass_eligible(result, grade):
        result["statuses"]["overall"] = "passed"
    elif not invalid_trial and result["statuses"]["product"] == "failed" and result.get("observer_stable") is not False:
        result["statuses"]["overall"] = "product-failed"
    if result.get("isolation", {}).get("status") == "fail" and not invalid_trial:
        result["statuses"]["overall"] = "run-isolation-failed"
    if _control_input_blocks(result):
        result["statuses"]["overall"] = "invalid-trial"


def full_pass_eligible(result: dict, grade: dict) -> bool:
    return (not result.get("partial") and grade.get("product_status") == "passed"
            and (not result["requires_incremental_review"] or grade.get("incremental_status") == "passed")
            and result.get("skill_stable")
            and result.get("observer_stable") is not False
            and result.get("isolation", {}).get("status") in (None, "pass")
            and not _control_input_blocks(result)
            and result.get("process", {}).get("exit_code") == 0
            and not result.get("process", {}).get("timed_out")
            and not result.get("process", {}).get("capture_error")
            and not result.get("process", {}).get("truncated")
            and result.get("process", {}).get("termination_reason") in (None, "exited", "completed")
            and result["statuses"]["protocol"] == "declared-complete-return-observed"
            and result.get("lifecycle", {}).get("complete")
            and result.get("host_observations", {}).get("shiploop_cli_completed")
            and not (result.get("host_observations", {}).get("shiploop_cli_exit_code_observed")
                     and not result.get("host_observations", {}).get("shiploop_cli_success_observed"))
            and result.get("host_observations", {}).get("terminal_end_observed")
            and not result.get("host_observations", {}).get("terminal", {}).get("error_observed")
            and not result.get("diagnostic"))


def run_suite(args: argparse.Namespace) -> int:
    from suites import resolve_suite
    suite = resolve_suite(args.suite, scenarios(), only_case_ids=args.only)
    cases = suite["cases"]
    if (args.repo or args.baseline) and len(cases) != 1:
        raise ValueError("--repo/--baseline require a single selected suite case (--only)")
    if args.baseline and not args.repo:
        raise ValueError("a selected feature baseline also requires its original --repo")
    root = Path(args.output).expanduser().absolute()
    if root.exists():
        raise ValueError("suite --output must be a new directory")
    campaign_root = root.resolve()
    caller_repo = _resolved_path(args.repo) if args.repo else None
    if caller_repo is not None and _paths_overlap(campaign_root, caller_repo):
        raise ValueError("caller --repo and suite campaign output must be separate, non-nested directories")
    root.mkdir(parents=True, mode=0o700)
    write_json(root / "suite-manifest.json", suite)
    product_keys = list(dict.fromkeys(case["product_key"] for case in cases))
    if caller_repo is not None:
        product_parent: Path | None = None
        product_repositories = {key: str(caller_repo) for key in product_keys}
    else:
        product_parent = _new_suite_product_parent(campaign_root, Path(OBSERVER_ROOT).resolve())
        product_repositories = {
            key: str(Path(tempfile.mkdtemp(prefix="p-", dir=product_parent)).resolve())
            for key in product_keys
        }
    write_json(root / "suite-execution.json", {
        "schema_version": 1,
        "suite_id": suite["id"],
        "campaign_root": str(campaign_root),
        "product_parent": str(product_parent) if product_parent is not None else None,
        "product_repositories": product_repositories,
        "cleanup": "No automatic cleanup; retain the physical product repositories for audit and feature lineage.",
    })
    rows, completed = [], {}
    for case in cases:
        output = root / "trials" / case["id"]
        dependency = case["depends_on"][0] if case["depends_on"] else None
        previous = completed.get(dependency)
        baseline = args.baseline or (str(previous / "result.json") if previous else None)
        repo = product_repositories[case["product_key"]]
        if case["depends_on"] and (not baseline or (previous and read_json(previous / "result.json")["statuses"]["overall"] != "passed")):
            row = {"case_id": case["id"], "step_id": case["step_id"], "status": "blocked-predecessor", "exit_code": None}
        else:
            trial = argparse.Namespace(**vars(args))
            trial.step, trial.repo, trial.output, trial.baseline = case["step_id"], repo, str(output), baseline
            trial.timeout = args.timeout if args.timeout is not None else case["timeout_seconds"]
            trial.max_turns = args.max_turns if args.max_turns is not None else case["max_turns"]
            trial.stop_after_stage = case["stop_after_stage"]
            trial.diagnostic_unverified_baseline = False
            trial.control_root = str(campaign_root)
            print(json.dumps({"suite": suite["id"], "case": case["id"], "event": "starting", "partial": bool(trial.stop_after_stage)}), flush=True)
            code = run_trial(trial)
            result = read_json(output / "result.json")
            row = {"case_id": case["id"], "step_id": case["step_id"], "status": result["statuses"]["overall"],
                   "exit_code": code, "trial": str(output), "skill_digest": result.get("skill_digest")}
            completed[case["step_id"]] = output
        rows.append(row)
        write_json(root / "suite-result.json", {"suite_id": suite["id"], "partial": suite["partial"], "cases": rows,
                                               "selected": len(cases), "finished": len(rows), "complete": len(rows) == len(cases)})
        print(json.dumps(row), flush=True)
    lines = ["# ShipLoop E2E suite", "", f"Suite: `{suite['id']}`", "",
             "Partial smoke passes establish only the selected SDLC prefix." if suite["partial"] else "Full passes require independent product verification.", "",
             "| Case | Status |", "| --- | --- |"]
    lines.extend(f"| {row['case_id']} | {row['status']} |" for row in rows)
    (root / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if all(row["exit_code"] == 0 for row in rows) else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="show exact scenario prompts without host calls")
    sub.add_parser("suites", help="list named partial/full suites without host calls")
    check = sub.add_parser("check", help="read installed skill selection/version and Git readiness; no model call")
    check.add_argument("--repo", required=True)
    check.add_argument("--model", default="not-selected")
    check.add_argument("--grok", default=shutil.which("grok") or str(Path.home() / ".local/bin/grok"))
    check.add_argument("--git")
    check.add_argument("--skill-root", default=str(Path.home() / ".grok/skills/shiploop"))
    run = sub.add_parser("run", help="launch exactly one fresh Grok process; live and opt-in")
    run.add_argument("--step", required=True)
    run.add_argument("--repo", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--model", required=True, help="explicit model ID supported by the installed Grok")
    run.add_argument("--grok", default=shutil.which("grok") or str(Path.home() / ".local/bin/grok"))
    run.add_argument("--git")
    run.add_argument("--skill-root", default=str(Path.home() / ".grok/skills/shiploop"), help="expected selected package, never a CLI override or install")
    run.add_argument("--timeout", type=float, default=7200, help="wall-clock cap in seconds (default: 7200 / 2 hours)")
    run.add_argument("--max-turns", type=int, default=1000, help="secondary turn cap (default: 1000)")
    run.add_argument("--stop-after-stage", choices=PARTIAL_STAGES, help="observe accepted stage and stop; only a partial smoke verdict")
    run.add_argument("--max-log-bytes", type=int, default=256 * 1024 * 1024, help="per-stream/event-file capture cap (default: 256 MiB)")
    run.add_argument("--max-event-line-chars", type=int, default=4 * 1024 * 1024, help="maximum native event line (default: 4 Mi characters)")
    run.add_argument("--reasoning-effort", default="xhigh", help="Grok reasoning effort (default: xhigh)")
    run.add_argument("--permission-mode", default="default", choices=["default", "acceptEdits", "auto", "dontAsk", "bypassPermissions"])
    run.add_argument("--artifact-root", action="append", default=[])
    run.add_argument("--baseline")
    run.add_argument("--diagnostic-unverified-baseline", action="store_true")
    run.add_argument("--verifier", help="external independent checker as JSON argv; stdout must be receipt JSON")
    run.add_argument("--verifier-timeout", type=float, default=300)
    suite = sub.add_parser("suite", help="run a named suite; each case launches a fresh Grok session")
    suite.add_argument("--suite", required=True)
    suite.add_argument("--output", required=True, help="new campaign directory for products and trials")
    suite.add_argument("--only", action="append", help="select case/step ID; repeat for several cases")
    suite.add_argument("--repo", help="original product repository for one selected case")
    suite.add_argument("--baseline", help="verified predecessor result for one selected feature case")
    suite.add_argument("--model", required=True)
    suite.add_argument("--grok", default=shutil.which("grok") or str(Path.home() / ".local/bin/grok"))
    suite.add_argument("--git")
    suite.add_argument("--skill-root", default=str(Path.home() / ".grok/skills/shiploop"))
    suite.add_argument("--timeout", type=float, help="override each case's time cap")
    suite.add_argument("--max-turns", type=int, help="override each case's turn cap")
    suite.add_argument("--max-log-bytes", type=int, default=256 * 1024 * 1024)
    suite.add_argument("--max-event-line-chars", type=int, default=4 * 1024 * 1024)
    suite.add_argument("--reasoning-effort", default="xhigh", help="Grok reasoning effort (default: xhigh)")
    suite.add_argument("--permission-mode", default="default", choices=["default", "acceptEdits", "auto", "dontAsk", "bypassPermissions"])
    suite.add_argument("--artifact-root", action="append", default=[])
    suite.add_argument("--verifier")
    suite.add_argument("--verifier-timeout", type=float, default=300)
    grade = sub.add_parser("grade", help="validate an independent evidence receipt against the unchanged trial candidate")
    grade.add_argument("--trial", required=True)
    grade.add_argument("--receipt", required=True)
    compare = sub.add_parser("compare", help="compare trial observations without selecting only successful attempts")
    compare.add_argument("trials", nargs="+", help="trial output directories")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            print(json.dumps(scenarios(), indent=2, ensure_ascii=False))
            return 0
        if args.command == "suites":
            from suites import list_suites
            print(json.dumps(list_suites(), indent=2))
            return 0
        if args.command == "check":
            git = resolve_git(args.git)
            env = dict(os.environ)
            env["PATH"] = str(Path(git).parent) + os.pathsep + env.get("PATH", "")
            checked = preflight(args, Path(args.repo).expanduser().resolve(), env)
            print(json.dumps({"selection": checked["selection"], "package_sha256": checked["package"]["aggregate_sha256"],
                              "package_files": len(checked["package"]["files"]), "grok_version": checked["grok_version"],
                              "git": git, "model": checked["model_requested"], "live_model_called": False}, indent=2))
            return 0
        if args.command in {"run", "suite"}:
            if ((args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0))
                    or (args.max_turns is not None and args.max_turns <= 0)
                    or args.max_log_bytes <= 0 or args.max_event_line_chars <= 0
                    or not math.isfinite(args.verifier_timeout) or args.verifier_timeout <= 0):
                raise ValueError("budgets must be positive")
            return run_suite(args) if args.command == "suite" else run_trial(args)
        if args.command == "grade":
            output = Path(args.trial).expanduser().resolve()
            result = read_json(output / "result.json")
            try:
                receipt = read_json(Path(args.receipt).expanduser().resolve())
                apply_grade(output, result, receipt)
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                result.setdefault("statuses", {})["overall"] = "invalid-trial"
                result["error"] = str(exc)
                report(output, result)
                raise
            write_json(output / "verification.json", receipt)
            report(output, result)
            return 0 if result["statuses"]["overall"] == "passed" else 2
        rows = []
        for trial in args.trials:
            result = read_json(Path(trial) / "result.json")
            row = {key: result.get(key) for key in ("trial_id", "step_id", "skill_digest", "candidate_digest", "statuses", "diagnostic")}
            row["observed_performance"] = result.get("audit", {})
            rows.append(row)
        print(json.dumps({"trials": rows, "note": "Descriptive comparisons; sequential feature steps are not independent replications."}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"shiploop-e2e: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
