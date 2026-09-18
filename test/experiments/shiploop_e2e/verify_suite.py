#!/usr/bin/env python3
"""Composite independent verifier for the nine ShipLoop game scenarios.

This observer is intentionally outside the one-shot model process.  It does
not choose selectors, build an app, mutate a product, or feed evidence back to
Grok.  A caller supplies read-only semantic UI adapters in a JSON registry;
the verifier records their bounded execution facts and compares observations
with independent rules.  Feature steps replay predecessor behavior against
both the immutable pre-feature snapshot and the returned product.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import driver_transport  # noqa: E402
import grading  # noqa: E402
import verify_tictactoe as tictactoe  # noqa: E402


VERIFIER_SCHEMA = "shiploop-e2e-composite-verifier/1"
TRACE_SCHEMA = "shiploop-e2e-composite-trace/1"
REVIEW_SCHEMA = "shiploop-e2e-independent-review/1"
DRIVER_REGISTRY_SCHEMA = "shiploop-e2e-drivers/1"
DEFAULT_DRIVER_TIMEOUT_SECONDS = 60.0
DEFAULT_DRIVER_MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_DRIVER_TIMEOUT_SECONDS = 300.0
MAX_DRIVER_OUTPUT_BYTES = 16 * 1024 * 1024
REVIEW_OWNED_CHECKS = frozenset(("local-only-scope", "run-returned-to-product"))
NON_SEMANTIC_CHECKS = frozenset((
    "local-only-scope", "run-returned-to-product", "gas-compatible-local-artifact",
    "previous-behavior-preserved", "feature-before-absent-or-already-satisfied",
    "feature-passes-after-when-eligible", "incremental-integration-review",
))
INCREMENTAL_CLASSIFICATIONS = frozenset(("integrated", "material-refactor", "replacement", "unverified"))
IGNORED_SOURCE_DIRECTORIES = frozenset((
    ".git", ".cache", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__",
    "node_modules", ".npm", ".shiploop", ".shiploop-runs",
))
MAX_SOURCE_ENTRIES = 100_000
MAX_SOURCE_FILE_BYTES = 128 * 1024 * 1024


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value) + b"\n")


def _artifact(evidence: Path, path: Path) -> dict[str, str]:
    relative = path.resolve().relative_to(evidence.resolve())
    return {"path": relative.as_posix(), "sha256": _sha256_file(path)}


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "unnamed"


def _unverified(check_id: str, detail: Any) -> dict[str, Any]:
    return {"id": check_id, "status": "unverified", "evidence": [], "details": detail}


def _row(check_id: str, status: str, evidence: list[dict[str, str]], detail: Any) -> dict[str, Any]:
    return {"id": check_id, "status": status, "evidence": evidence, "details": detail}


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def source_fingerprint(root: Path) -> dict[str, Any]:
    """Hash product source while excluding Git and conventional runtime caches.

    It intentionally does not use Git object state: a semantic adapter may
    start local tooling that changes `.git` metadata or cache directories, but
    it must not alter application source outside those transient locations.
    Symlinks are represented by their link text and never traversed.
    """
    resolved_root = Path(root).resolve()
    if not resolved_root.is_dir():
        raise ValueError("source fingerprint root must be an existing directory")
    rows: list[dict[str, Any]] = []
    ignored: list[str] = []
    scanned = 0

    def file_hash(path: Path) -> tuple[str, int]:
        size = path.stat().st_size
        if size > MAX_SOURCE_FILE_BYTES:
            raise ValueError(f"source file exceeds fingerprint bound: {path.name}")
        return _sha256_file(path), size

    def walk(directory: Path, relative: Path) -> None:
        nonlocal scanned
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise ValueError(f"cannot enumerate source directory: {directory}") from exc
        for child in children:
            scanned += 1
            if scanned > MAX_SOURCE_ENTRIES:
                raise ValueError("source fingerprint entry bound exceeded")
            child_relative = relative / child.name
            try:
                mode = stat.S_IMODE(child.lstat().st_mode)
            except OSError as exc:
                raise ValueError(f"cannot stat source entry: {child}") from exc
            if child.is_symlink():
                try:
                    target = os.readlink(child)
                except OSError as exc:
                    raise ValueError(f"cannot read source symlink: {child}") from exc
                rows.append({"path": child_relative.as_posix(), "kind": "symlink", "mode": mode,
                             "target_sha256": _sha256_bytes(target.encode("utf-8", errors="surrogateescape"))})
            elif child.is_dir():
                if child.name in IGNORED_SOURCE_DIRECTORIES:
                    ignored.append(child_relative.as_posix())
                    continue
                walk(child, child_relative)
            elif child.is_file():
                digest, size = file_hash(child)
                rows.append({"path": child_relative.as_posix(), "kind": "file", "mode": mode,
                             "bytes": size, "sha256": digest})
            else:
                rows.append({"path": child_relative.as_posix(), "kind": "other", "mode": mode})

    walk(resolved_root, Path())
    # Report cache presence without binding it: local tooling may create or
    # remove these deliberately excluded directories while observing the app.
    payload = {"files": rows}
    return {
        "schema": "shiploop-e2e-source-fingerprint/1",
        "root": str(resolved_root),
        "files": rows,
        "ignored": ignored,
        "digest": _sha256_bytes(_json_bytes(payload)),
    }


def _catalog_context(step_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("scenarios"), list):
        raise ValueError("unsupported scenario catalog")
    matches = [
        (family, step)
        for family in catalog["scenarios"] if isinstance(family, dict)
        for step in family.get("steps", []) if isinstance(step, dict) and step.get("id") == step_id
    ]
    if len(matches) != 1:
        raise ValueError("unknown or duplicate scenario step")
    family, step = matches[0]
    if not isinstance(family.get("id"), str) or not isinstance(step.get("required_checks"), list):
        raise ValueError("scenario lacks family/check declarations")
    return family, step


def _context(environ: Mapping[str, str]) -> dict[str, Any]:
    required = ("SHIPLOOP_E2E_TRIAL", "SHIPLOOP_E2E_REPO", "SHIPLOOP_E2E_EVIDENCE")
    if any(not environ.get(name) for name in required):
        raise ValueError("SHIPLOOP_E2E_TRIAL, SHIPLOOP_E2E_REPO, and SHIPLOOP_E2E_EVIDENCE are required")
    trial = Path(str(environ["SHIPLOOP_E2E_TRIAL"])).resolve()
    repo = Path(str(environ["SHIPLOOP_E2E_REPO"])).resolve()
    evidence = Path(str(environ["SHIPLOOP_E2E_EVIDENCE"])).resolve()
    result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(result.get("step_id"), str):
        raise ValueError("trial result lacks a scenario step")
    family, step = _catalog_context(result["step_id"])
    if result.get("required_checks") not in (None, step["required_checks"]):
        raise ValueError("trial required checks do not match scenarios.json")
    if not isinstance(result.get("trial_id"), str) or not result["trial_id"]:
        raise ValueError("trial result lacks trial_id")
    if not isinstance(result.get("candidate_digest"), str) or not result["candidate_digest"]:
        raise ValueError("trial result lacks candidate_digest")
    baseline_digest = result.get("baseline_digest")
    if baseline_digest is not None and (not isinstance(baseline_digest, str) or not baseline_digest):
        raise ValueError("trial result has invalid baseline_digest")
    baseline_value = environ.get("SHIPLOOP_E2E_BASELINE") or str(trial / "product-before")
    baseline = Path(baseline_value).resolve()
    if baseline_digest is not None and not baseline.is_dir():
        raise ValueError("incremental trial lacks immutable product-before snapshot")
    if not repo.is_dir():
        raise ValueError("candidate repository is unavailable")
    evidence.mkdir(parents=True, exist_ok=True)
    return {"trial": trial, "repo": repo, "baseline": baseline, "evidence": evidence,
            "result": result, "family": family, "step": step}


def _parse_driver_definition(value: Any, *, registry_base: Path) -> dict[str, Any]:
    if isinstance(value, list):
        return {"argv": driver_transport.resolve_argv(value, base=registry_base)}
    if not isinstance(value, dict):
        raise ValueError("driver definition must be argv or an object containing argv")
    argv = driver_transport.resolve_argv(value.get("argv"), base=registry_base)
    timeout = value.get("timeout_seconds", value.get("timeout", DEFAULT_DRIVER_TIMEOUT_SECONDS))
    maximum = value.get("max_output_bytes", DEFAULT_DRIVER_MAX_OUTPUT_BYTES)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < float(timeout) <= MAX_DRIVER_TIMEOUT_SECONDS:
        raise ValueError("driver timeout must be positive and within the hard bound")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 0 < maximum <= MAX_DRIVER_OUTPUT_BYTES:
        raise ValueError("driver max_output_bytes must be positive and within the hard bound")
    try:
        _json_bytes(value.get("config", {}))
    except (TypeError, ValueError) as exc:
        raise ValueError("driver config must be JSON serializable") from exc
    return {"argv": argv, "timeout_seconds": float(timeout), "max_output_bytes": maximum,
            "config": value.get("config", {})}


def load_driver_registry(path: Path | None) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Load explicit step/family adapter argv definitions without a shell."""
    if path is None:
        return {}, {"status": "not-supplied", "source_path": None}
    try:
        requested = Path(path)
        if requested.is_symlink():
            raise ValueError("drivers file must not be a symbolic link")
        source = requested.resolve(strict=True)
        if not source.is_file():
            raise ValueError("drivers file must be a regular file")
        raw_bytes = source.read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, {"status": "invalid", "reason": type(exc).__name__, "source_path": str(path)}
    if not isinstance(raw, dict):
        return {}, {"status": "invalid", "reason": "drivers-not-object", "source_path": str(source)}
    if "schema" in raw and raw.get("schema") != DRIVER_REGISTRY_SCHEMA:
        return {}, {"status": "invalid", "reason": "schema-mismatch", "source_path": str(source)}
    mapping = raw.get("drivers", raw)
    if not isinstance(mapping, dict):
        return {}, {"status": "invalid", "reason": "drivers-not-object", "source_path": str(source)}
    parsed: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for key, definition in mapping.items():
        if key == "schema" and mapping is raw:
            continue
        if not isinstance(key, str) or not key:
            errors[str(key)] = "invalid-key"
            continue
        try:
            parsed[key] = _parse_driver_definition(definition, registry_base=source.parent)
        except ValueError as exc:
            errors[key] = str(exc)
    return parsed, {"status": "loaded" if not errors else "partially-invalid",
                    "source_path": str(source), "source_sha256": _sha256_bytes(raw_bytes),
                    "entries": sorted(parsed), "errors": errors}


def _driver_for(
    registry: Mapping[str, dict[str, Any]], step_id: str, family_id: str,
    default_timeout: float, default_maximum: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    selected_key = step_id if step_id in registry else family_id if family_id in registry else None
    if selected_key is None:
        return None, {"reason": "driver-not-configured", "step_id": step_id, "family": family_id}
    raw = registry[selected_key]
    timeout = raw.get("timeout_seconds", default_timeout)
    maximum = raw.get("max_output_bytes", default_maximum)
    if not 0 < float(timeout) <= MAX_DRIVER_TIMEOUT_SECONDS:
        return None, {"reason": "driver-timeout-invalid", "selection": selected_key}
    if not 0 < int(maximum) <= MAX_DRIVER_OUTPUT_BYTES:
        return None, {"reason": "driver-output-bound-invalid", "selection": selected_key}
    configuration = {"selection": selected_key, "argv": raw["argv"], "timeout_seconds": float(timeout),
                     "max_output_bytes": int(maximum), "config": raw.get("config", {})}
    return {**raw, "timeout_seconds": float(timeout), "max_output_bytes": int(maximum),
            "selection": selected_key, "configuration": configuration}, {"selection": selected_key}


def _ttt_cases(step_id: str) -> list[dict[str, Any]]:
    """Expose the established Tic-Tac-Toe action/rule oracle without a UI."""
    rows = [
        {"id": "ttt-base-game", "game": "tic-tac-toe", "step_id": "ttt-create", "level": "base",
         "actions": tictactoe._base_actions()},
        {"id": "ttt-turn-indicator-and-legal-highlights", "game": "tic-tac-toe",
         "step_id": "ttt-guidance", "level": "guidance", "actions": tictactoe._guidance_actions()},
        {"id": "ttt-best-move-hint", "game": "tic-tac-toe", "step_id": "ttt-best-move",
         "level": "refine", "actions": tictactoe._best_move_actions()},
    ]
    order = {"ttt-create": 0, "ttt-guidance": 1, "ttt-best-move": 2}
    if step_id not in order:
        raise ValueError("unsupported Tic-Tac-Toe scenario step")
    return rows[:order[step_id] + 1]


def _oracle_games_module() -> Any:
    try:
        module = importlib.import_module("oracle_games")
    except ModuleNotFoundError as exc:
        raise ValueError("game-oracle-module-unavailable") from exc
    if not callable(getattr(module, "cases", None)) or not callable(getattr(module, "evaluate", None)):
        raise ValueError("game-oracle-module-contract-invalid")
    return module


def _validate_behavior_case(case: Any, *, family_id: str, requested_step: str) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ValueError("oracle case is not an object")
    required = ("id", "game", "step_id", "level", "actions")
    if any(not isinstance(case.get(key), str) or not case[key] for key in required[:-1]):
        raise ValueError("oracle case lacks stable identifiers")
    if not isinstance(case.get("actions"), list):
        raise ValueError("oracle case lacks action list")
    if case["game"] != family_id:
        raise ValueError("oracle case family does not match scenario")
    try:
        _json_bytes(case)
    except (TypeError, ValueError) as exc:
        raise ValueError("oracle case is not JSON serializable") from exc
    return case


def _behavior_cases(family: Mapping[str, Any], step: Mapping[str, Any]) -> list[dict[str, Any]]:
    family_id = str(family["id"])
    step_id = str(step["id"])
    if family_id == "tic-tac-toe":
        cases = _ttt_cases(step_id)
    else:
        cases = _oracle_games_module().cases(step_id)
    if not isinstance(cases, list) or not cases:
        raise ValueError("oracle did not return behavior cases")
    checked = [_validate_behavior_case(case, family_id=family_id, requested_step=step_id) for case in cases]
    if len({case["id"] for case in checked}) != len(checked):
        raise ValueError("oracle returned duplicate behavior case IDs")
    if not any(case["step_id"] == step_id for case in checked):
        raise ValueError("oracle omitted the requested behavior")
    return checked


def _evaluate_ttt_case(case: Mapping[str, Any], observations: list[Any]) -> list[dict[str, Any]]:
    actions = case["actions"]
    if len(observations) != len(actions):
        raise ValueError("driver-observation-count-mismatch")
    try:
        canonical = [tictactoe._canonical_observation(value) for value in observations]
    except Exception as exc:
        raise ValueError("invalid-tictactoe-observation") from exc
    expected, issues = tictactoe._rule_issues(actions, canonical)
    if case["id"] == "ttt-turn-indicator-and-legal-highlights":
        issues.extend(tictactoe._guidance_issues(expected, canonical))
    elif case["id"] == "ttt-best-move-hint":
        issues.extend(tictactoe._best_move_issues(expected, canonical))
    return issues


def _evaluate_behavior(case: Mapping[str, Any], observations: list[Any]) -> list[dict[str, Any]]:
    if case["game"] == "tic-tac-toe":
        return _evaluate_ttt_case(case, observations)
    if len(observations) != len(case["actions"]):
        raise ValueError("driver-observation-count-mismatch")
    issues = _oracle_games_module().evaluate(dict(case), observations)
    if not isinstance(issues, list) or any(not isinstance(issue, dict) for issue in issues):
        raise ValueError("game-oracle-returned-invalid-issues")
    return issues


def _trace_path(evidence: Path, target: str, case_id: str) -> Path:
    return evidence / "behavior" / _safe_name(target) / f"{_safe_name(case_id)}.json"


def _source_summary(value: dict[str, Any]) -> dict[str, Any]:
    return {"digest": value.get("digest"), "file_count": len(value.get("files", [])),
            "ignored": value.get("ignored", [])}


def _run_behavior_case(
    *,
    case: dict[str, Any], target: str, repo: Path, family: Mapping[str, Any], step: Mapping[str, Any],
    registry: Mapping[str, dict[str, Any]], evidence: Path, default_timeout: float,
    default_maximum: int, mutated_roots: set[str],
) -> dict[str, Any]:
    """Run one external semantic case, preserving a source-integrity trace."""
    trace_path = _trace_path(evidence, target, str(case["id"]))
    root_key = str(repo.resolve())
    trace: dict[str, Any] = {
        "schema": TRACE_SCHEMA,
        "target": target,
        "case_id": case["id"],
        "case_step_id": case["step_id"],
        "requested_step_id": step["id"],
        "family": family["id"],
        "adapter_boundary": "external-read-only-semantic-driver",
    }
    if root_key in mutated_roots:
        trace.update(status="unverified", reason="prior-driver-source-mutation")
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    try:
        before = source_fingerprint(repo)
    except ValueError as exc:
        trace.update(status="unverified", reason="source-fingerprint-before-failed", error=type(exc).__name__)
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    driver, selection = _driver_for(registry, str(step["id"]), str(family["id"]), default_timeout, default_maximum)
    trace["source_before"] = _source_summary(before)
    trace["driver_selection"] = selection
    if driver is None:
        trace.update(status="unverified", reason=selection["reason"])
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    request = {
        "schema": driver_transport.REQUEST_SCHEMA,
        "step_id": step["id"],
        "family": family["id"],
        "repo": str(repo.resolve()),
        "case": case,
        "actions": case["actions"],
    }
    try:
        invoked = driver_transport.invoke(
            driver["argv"], request, cwd=repo, timeout_seconds=driver["timeout_seconds"],
            max_output_bytes=driver["max_output_bytes"], configuration=driver["configuration"],
        )
        after = source_fingerprint(repo)
    except driver_transport.DriverTransportError as exc:
        try:
            after = source_fingerprint(repo)
        except ValueError:
            after = None
        trace.update(status="unverified", reason=exc.code, source_after=_source_summary(after) if after else None)
        if after is None or after.get("digest") != before.get("digest"):
            mutated_roots.add(root_key)
            trace["source_mutated"] = True
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    except (OSError, ValueError) as exc:
        try:
            after = source_fingerprint(repo)
        except ValueError:
            after = None
        trace.update(status="unverified", reason="driver-invocation-invalid", error=type(exc).__name__,
                     source_after=_source_summary(after) if after else None)
        if after is None or after.get("digest") != before.get("digest"):
            mutated_roots.add(root_key)
            trace["source_mutated"] = True
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}

    transport = {key: value for key, value in invoked.items() if key != "observations"}
    trace.update(driver=transport, observations=invoked["observations"], source_after=_source_summary(after))
    if after["digest"] != before["digest"]:
        mutated_roots.add(root_key)
        trace.update(status="unverified", reason="driver-source-mutation", source_mutated=True)
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    try:
        issues = _evaluate_behavior(case, invoked["observations"])
    except (ValueError, TypeError, KeyError) as exc:
        trace.update(status="unverified", reason="oracle-observation-invalid", error=type(exc).__name__)
        _write_json(trace_path, trace)
        return {"status": "unverified", "issues": [], "evidence": [_artifact(evidence, trace_path)],
                "details": trace["reason"], "trace": trace}
    trace.update(status="pass" if not issues else "fail", issues=issues)
    _write_json(trace_path, trace)
    return {"status": trace["status"], "issues": issues, "evidence": [_artifact(evidence, trace_path)],
            "details": "external semantic trace matched independent rules" if not issues else issues, "trace": trace}


def _closure_result(repo: Path, evidence: Path, mutated_roots: set[str]) -> dict[str, Any]:
    """Run the target-runtime source-closure inspector without inferring UI use."""
    trace_path = evidence / "gas-closure.json"
    root_key = str(repo.resolve())
    trace: dict[str, Any] = {"schema": TRACE_SCHEMA, "kind": "gas-source-closure",
                             "adapter_boundary": "read-only-source-closure-inspector"}
    if root_key in mutated_roots:
        trace.update(status="unverified", reason="prior-driver-source-mutation")
        _write_json(trace_path, trace)
        return {"status": "unverified", "evidence": [_artifact(evidence, trace_path)], "details": trace["reason"]}
    try:
        before = source_fingerprint(repo)
        module = importlib.import_module("gas_artifact")
        inspector = getattr(module, "inspect_artifact", None)
        if not callable(inspector):
            raise ValueError("gas-artifact-contract-invalid")
        report = inspector(repo)
        after = source_fingerprint(repo)
    except (ImportError, OSError, ValueError, TypeError) as exc:
        try:
            after = source_fingerprint(repo)
        except ValueError:
            after = None
        trace.update(status="unverified", reason="gas-closure-unavailable", error=type(exc).__name__,
                     source_after=_source_summary(after) if after else None)
        if "before" in locals() and (after is None or after.get("digest") != before.get("digest")):
            mutated_roots.add(root_key)
            trace["source_mutated"] = True
        _write_json(trace_path, trace)
        return {"status": "unverified", "evidence": [_artifact(evidence, trace_path)], "details": trace["reason"]}
    trace.update(source_before=_source_summary(before), source_after=_source_summary(after), report=report)
    if after["digest"] != before["digest"]:
        mutated_roots.add(root_key)
        trace.update(status="unverified", reason="closure-inspector-source-mutation", source_mutated=True)
    elif not isinstance(report, dict) or report.get("status") not in {"pass", "fail", "unverified"}:
        trace.update(status="unverified", reason="gas-closure-invalid-result")
    else:
        trace["status"] = report["status"]
    _write_json(trace_path, trace)
    return {"status": trace["status"], "evidence": [_artifact(evidence, trace_path)],
            "details": trace.get("report", {}).get("issues", trace.get("reason")) if isinstance(trace.get("report"), dict) else trace.get("reason")}


def _aggregate_trace(evidence: Path, name: str, value: dict[str, Any]) -> list[dict[str, str]]:
    path = evidence / "replay" / f"{_safe_name(name)}.json"
    _write_json(path, value)
    return [_artifact(evidence, path)]


def _behavior_matrix(
    context: Mapping[str, Any], registry: Mapping[str, dict[str, Any]], *,
    default_timeout: float, default_maximum: int, mutated_roots: set[str],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    cases = _behavior_cases(context["family"], context["step"])
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    baseline_required = context["result"].get("baseline_digest") is not None
    for case in cases:
        if baseline_required:
            matrix[(case["id"], "before")] = _run_behavior_case(
                case=case, target="before", repo=context["baseline"], family=context["family"],
                step=context["step"], registry=registry, evidence=context["evidence"],
                default_timeout=default_timeout, default_maximum=default_maximum,
                mutated_roots=mutated_roots,
            )
        matrix[(case["id"], "after")] = _run_behavior_case(
            case=case, target="after", repo=context["repo"], family=context["family"],
            step=context["step"], registry=registry, evidence=context["evidence"],
            default_timeout=default_timeout, default_maximum=default_maximum,
            mutated_roots=mutated_roots,
        )
    return cases, matrix


def _status_from_results(results: list[dict[str, Any]]) -> str:
    if not results or any(result["status"] == "unverified" for result in results):
        return "unverified"
    if any(result["status"] == "fail" for result in results):
        return "fail"
    return "pass"


def _checkers_variant_fingerprint(result: Mapping[str, Any]) -> str | None:
    trace = result.get("trace")
    observations = trace.get("observations") if isinstance(trace, Mapping) else None
    if not isinstance(observations, list) or not observations:
        return None
    variants = [row.get("variant") for row in observations if isinstance(row, Mapping)]
    if len(variants) != len(observations) or any(not isinstance(value, dict) for value in variants):
        return None
    return _sha256_bytes(_json_bytes(variants[0])) if all(value == variants[0] for value in variants) else None


def _replay_rows(
    context: Mapping[str, Any], cases: list[dict[str, Any]], matrix: Mapping[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Convert executable before/after traces into the scenario's delta rows."""
    step = context["step"]
    result = context["result"]
    evidence = context["evidence"]
    rows: dict[str, dict[str, Any]] = {}
    current = [case for case in cases if case["step_id"] == step["id"]]
    predecessors = [case for case in cases if case["step_id"] != step["id"]]
    current_after = [matrix[(case["id"], "after")] for case in current]
    semantic_checks = [check_id for check_id in step["required_checks"] if check_id not in NON_SEMANTIC_CHECKS]

    summary = {
        "schema": TRACE_SCHEMA,
        "kind": "behavior-replay-summary",
        "step_id": step["id"],
        "cases": [
            {"id": case["id"], "case_step_id": case["step_id"],
             "before": matrix.get((case["id"], "before"), {}).get("status"),
             "after": matrix.get((case["id"], "after"), {}).get("status")}
            for case in cases
        ],
    }
    variant_comparisons: list[dict[str, Any]] = []
    if context["family"]["id"] == "checkers" and result.get("baseline_digest") is not None:
        for case in cases:
            before_result = matrix[(case["id"], "before")]
            after_result = matrix[(case["id"], "after")]
            before_variant = _checkers_variant_fingerprint(before_result)
            after_variant = _checkers_variant_fingerprint(after_result)
            if before_variant is not None and after_variant is not None:
                variant_comparisons.append({"case_id": case["id"], "before": before_variant,
                                            "after": after_variant, "matches": before_variant == after_variant})
        summary["checkers_variant_comparisons"] = variant_comparisons
    current_status = _status_from_results(current_after)
    predecessor_status = None
    classification = "not-applicable"
    after_status = None
    if result.get("baseline_digest") is not None:
        predecessor_results = [matrix[(case["id"], endpoint)] for case in predecessors for endpoint in ("before", "after")]
        predecessor_status = _status_from_results(predecessor_results)
        if any(not row["matches"] for row in variant_comparisons if row["case_id"] in {case["id"] for case in predecessors}):
            predecessor_status = "fail"
        before_current = [matrix[(case["id"], "before")] for case in current]
        after_status = _status_from_results(current_after)
        before_status = _status_from_results(before_current)
        if before_status == "pass":
            classification = "baseline-already-satisfies-feature"
        elif before_status == "fail":
            classification = "feature-absent-before-run"
        else:
            classification = "unverified"
        summary["feature_delta"] = {"before_status": before_status, "after_status": after_status,
                                    "classification": classification}
    # Bind every row to the final single-write aggregate.  Never overwrite an
    # artifact after its digest has appeared in the receipt.
    summary_evidence = _aggregate_trace(evidence, f"{step['id']}-behavior-replay", summary)
    for check_id in semantic_checks:
        rows[check_id] = _row(
            check_id, current_status, summary_evidence,
            "all current-step semantic cases passed" if current_status == "pass"
            else "one or more current-step semantic cases failed or were incomplete",
        )
    if result.get("baseline_digest") is None:
        return rows, {"summary": summary, "evidence": summary_evidence}

    if "previous-behavior-preserved" in step["required_checks"]:
        rows["previous-behavior-preserved"] = _row(
            "previous-behavior-preserved", predecessor_status, summary_evidence,
            "all predecessor behavior traces passed before and after" if predecessor_status == "pass"
            else "predecessor replay was failing or incomplete",
        )
    if "feature-before-absent-or-already-satisfied" in step["required_checks"]:
        rows["feature-before-absent-or-already-satisfied"] = _row(
            "feature-before-absent-or-already-satisfied",
            "pass" if classification != "unverified" else "unverified", summary_evidence, classification,
        )
    if "feature-passes-after-when-eligible" in step["required_checks"]:
        if classification == "feature-absent-before-run":
            status = after_status
            detail = "feature eligible because it was absent before the run"
        elif classification == "baseline-already-satisfies-feature":
            status = "fail" if after_status == "fail" else "unverified"
            detail = "baseline-already-satisfies-feature: non-causal, not feature success"
        else:
            status = "unverified"
            detail = "feature baseline could not be observed completely"
        rows["feature-passes-after-when-eligible"] = _row(
            "feature-passes-after-when-eligible", status, summary_evidence, detail,
        )
    return rows, {"summary": summary, "evidence": summary_evidence, "classification": classification}


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _review_forbidden_roots(context: Mapping[str, Any]) -> tuple[Path, ...]:
    """Product roots cannot supply the independent-review record or evidence."""
    roots = [Path(context["repo"]).resolve()]
    baseline = Path(context["baseline"])
    if baseline.is_dir():
        roots.append(baseline.resolve())
    return tuple(roots)


def _materialize_review_evidence(
    entries: Any, *, source_root: Path, evidence: Path, namespace: str, check_id: str,
    require_nonempty: bool, forbidden_roots: tuple[Path, ...],
) -> tuple[list[dict[str, str]], list[str]]:
    """Copy reviewer-pinned files into the trial evidence root before grading."""
    if not isinstance(entries, list):
        return [], ["review-evidence-not-list"]
    if require_nonempty and not entries:
        return [], ["review-evidence-required"]
    refs: list[dict[str, str]] = []
    errors: list[str] = []
    source_root = source_root.resolve()
    destination = evidence / "review-material" / _safe_name(namespace) / _safe_name(check_id)
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not _valid_digest(entry.get("sha256")):
            errors.append("invalid-review-evidence-entry")
            continue
        relative = Path(entry["path"])
        if relative.is_absolute() or not relative.parts or any(part == ".." for part in relative.parts):
            errors.append("unsafe-review-evidence-path")
            continue
        source = source_root / relative
        try:
            resolved = source.resolve(strict=True)
            if not _inside(source_root, resolved) or source.is_symlink() or not resolved.is_file():
                errors.append("unsafe-review-evidence-source")
                continue
            if any(_inside(root, resolved) for root in forbidden_roots):
                errors.append("review-evidence-inside-product")
                continue
            data = resolved.read_bytes()
        except OSError:
            errors.append("review-evidence-unavailable")
            continue
        if len(data) > MAX_SOURCE_FILE_BYTES:
            errors.append("review-evidence-exceeds-bound")
            continue
        try:
            from capture import _sanitize_text
            decoded = data.decode("utf-8")
            if _sanitize_text(decoded) != decoded:
                errors.append("review-evidence-credential-shaped")
                continue
        except UnicodeDecodeError:
            pass
        if _sha256_bytes(data) != entry["sha256"].lower():
            errors.append("review-evidence-digest-mismatch")
            continue
        target = destination / f"{index:02d}-{entry['sha256'].lower()}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            errors.append("review-evidence-destination-collision")
            continue
        if not target.exists():
            target.write_bytes(data)
        refs.append(_artifact(evidence, target))
    # Reuse the receipt validator's path/digest rules after copying: reviewed
    # evidence is now pinned at the same root that grading will receive.
    _, validation_errors = grading._evidence_results(  # type: ignore[attr-defined]
        refs, root=evidence, check_id=check_id, require_evidence_for="pass" if require_nonempty else None,
    )
    errors.extend(str(row.get("code", "invalid-evidence")) for row in validation_errors)
    return refs, sorted(set(errors))


def _read_review(path: Path | None, context: Mapping[str, Any]) -> dict[str, Any]:
    """Load one review record or select this step from a review registry."""
    if path is None:
        return {"available": False, "reason": "review-not-supplied"}
    try:
        requested = Path(path)
        if requested.is_symlink():
            raise ValueError("review must not be a symbolic link")
        source = requested.resolve(strict=True)
        if not source.is_file():
            raise ValueError("review-not-regular-file")
        if any(_inside(root, source) for root in _review_forbidden_roots(context)):
            return {"available": False, "reason": "review-inside-product"}
        raw_bytes = source.read_bytes()
        raw_text = raw_bytes.decode("utf-8")
        from capture import _sanitize_text
        if _sanitize_text(raw_text) != raw_text:
            raise ValueError("review-credential-shaped")
        raw = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {"available": False, "reason": "review-unavailable", "error": type(exc).__name__}
    if not isinstance(raw, dict):
        return {"available": False, "reason": "review-not-object", "source_sha256": _sha256_bytes(raw_bytes)}
    if "step_id" in raw:
        selected = raw
    else:
        registry = raw.get("reviews", raw)
        selected = registry.get(context["step"]["id"]) if isinstance(registry, dict) else None
    if not isinstance(selected, dict):
        return {"available": False, "reason": "review-step-not-found", "source_sha256": _sha256_bytes(raw_bytes)}
    return {"available": True, "source": source, "source_sha256": _sha256_bytes(raw_bytes), "record": selected}


def _review_assessment(path: Path | None, context: Mapping[str, Any]) -> dict[str, Any]:
    """Assess only independently reviewer-owned scope/return/lineage claims."""
    evidence = context["evidence"]
    loaded = _read_review(path, context)
    trace: dict[str, Any] = {"schema": TRACE_SCHEMA, "kind": "independent-review", "available": loaded["available"]}
    result: dict[str, Any] = {"owned_rows": {}, "integration": {"status": "unverified", "evidence": [],
                                                                          "details": "independent review unavailable"},
                              "incremental_review": {"status": "unverified", "evidence": []}}
    if not loaded["available"]:
        trace.update(reason=loaded["reason"], error=loaded.get("error"))
        path_out = evidence / "review" / "assessment.json"
        _write_json(path_out, trace)
        result["trace_evidence"] = [_artifact(evidence, path_out)]
        return result

    record = loaded["record"]
    record_digest = _sha256_bytes(_json_bytes(record))
    copied_record = evidence / "review" / f"input-{record_digest}.json"
    _write_json(copied_record, record)
    expected = {
        "schema": REVIEW_SCHEMA,
        "step_id": context["step"]["id"],
        "trial_id": context["result"]["trial_id"],
        "candidate_digest": context["result"]["candidate_digest"],
        "baseline_digest": context["result"].get("baseline_digest"),
    }
    binding_errors = [field for field, value in expected.items() if record.get(field) != value]
    rationale = record.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        binding_errors.append("rationale")
    trace.update(source_sha256=loaded["source_sha256"], record_sha256=record_digest,
                 expected_bindings=expected, binding_valid=not binding_errors,
                 binding_errors=binding_errors, input_artifact=_artifact(evidence, copied_record))
    if binding_errors:
        trace["reason"] = "review-binding-invalid"
        path_out = evidence / "review" / "assessment.json"
        _write_json(path_out, trace)
        result["trace_evidence"] = [_artifact(evidence, path_out)]
        return result

    source_root = Path(loaded["source"]).parent
    forbidden_roots = _review_forbidden_roots(context)
    owned = record.get("review_owned_checks", [])
    if not isinstance(owned, list):
        trace["owned_check_errors"] = ["review-owned-checks-not-list"]
        owned = []
    seen: set[str] = set()
    accepted_owned: dict[str, dict[str, Any]] = {}
    rejected_owned: list[str] = []
    for entry in owned:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            rejected_owned.append("invalid-review-owned-check")
            continue
        check_id = entry["id"]
        if check_id in seen or check_id not in REVIEW_OWNED_CHECKS:
            rejected_owned.append(check_id)
            continue
        seen.add(check_id)
        status = entry.get("status")
        if status not in {"pass", "fail", "unverified"}:
            rejected_owned.append(check_id)
            continue
        refs, errors = _materialize_review_evidence(
            entry.get("evidence", []), source_root=source_root, evidence=evidence,
            namespace=record_digest, check_id=check_id, require_nonempty=status in {"pass", "fail"},
            forbidden_roots=forbidden_roots,
        )
        if errors:
            accepted_owned[check_id] = _unverified(check_id, {"reason": "review-evidence-invalid", "errors": errors})
        else:
            accepted_owned[check_id] = _row(check_id, status, refs, entry.get("details", rationale))
    result["owned_rows"] = accepted_owned
    trace["review_owned_checks"] = {key: value["status"] for key, value in accepted_owned.items()}
    if rejected_owned:
        trace["rejected_review_owned_checks"] = rejected_owned

    if context["result"].get("baseline_digest") is not None:
        classification = record.get("classification")
        prior_entry = record.get("prior_entry_reachable")
        feature_integrated = record.get("feature_integrated")
        refs, errors = _materialize_review_evidence(
            record.get("evidence", []), source_root=source_root, evidence=evidence,
            namespace=record_digest, check_id="incremental-review", require_nonempty=True,
            forbidden_roots=forbidden_roots,
        )
        detail = {"classification": classification, "prior_entry_reachable": prior_entry,
                  "feature_integrated": feature_integrated, "rationale": rationale}
        if classification not in INCREMENTAL_CLASSIFICATIONS or not isinstance(prior_entry, bool) or not isinstance(feature_integrated, bool) or errors:
            status = "unverified"
            detail["reason"] = "incremental-review-fields-or-evidence-invalid"
            detail["errors"] = errors
        elif classification == "integrated" and prior_entry and feature_integrated:
            status = "pass"
        elif classification == "replacement":
            status = "fail"
        elif classification == "material-refactor":
            # It may be legitimate, but it is not a supported incremental
            # preservation conclusion until a human resolves its scope.
            status = "unverified"
            detail["reason"] = "behavior-preserved-but-material-refactor"
        else:
            status = "unverified"
            detail["reason"] = "reviewer-could-not-support-incremental-conclusion"
        result["integration"] = {"status": status, "evidence": refs, "details": detail}
        result["incremental_review"] = {"status": status, "evidence": refs, "details": detail}
        trace["incremental_review"] = {"status": status, **detail}
    path_out = evidence / "review" / "assessment.json"
    _write_json(path_out, trace)
    result["trace_evidence"] = [_artifact(evidence, path_out)]
    return result


def _input_file_row(name: str, path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.is_symlink():
            return {"name": name, "path": str(path), "status": "unavailable"}
        return {"name": name, "path": str(path.resolve()), "status": "present", "sha256": _sha256_file(path)}
    except OSError:
        return {"name": name, "path": str(path), "status": "unavailable"}


def _looks_like_adapter_file(value: str) -> bool:
    return value.startswith(".") or "/" in value or Path(value).suffix.lower() in {".py", ".js", ".cjs", ".mjs", ".sh"}


def verifier_inputs_manifest(
    registry: Mapping[str, Mapping[str, Any]], registry_info: Mapping[str, Any],
) -> dict[str, Any]:
    """Fingerprint the observer/oracle/adapter inputs used for this receipt."""
    module_names = ("verify_suite.py", "driver_transport.py", "verify_tictactoe.py", "grading.py",
                    "oracle_games.py", "gas_artifact.py", "scenarios.json")
    modules = [_input_file_row(name, HERE / name) for name in module_names]
    source_path = registry_info.get("source_path")
    registry_base = Path(source_path).parent if isinstance(source_path, str) and source_path else None
    adapters: list[dict[str, Any]] = []
    for key in sorted(registry):
        definition = registry[key]
        files: list[dict[str, Any]] = []
        for index, token in enumerate(definition.get("argv", [])):
            if not isinstance(token, str) or not _looks_like_adapter_file(token):
                continue
            candidate = Path(token)
            if not candidate.is_absolute() and registry_base is not None:
                candidate = registry_base / candidate
            if candidate.is_absolute() or registry_base is not None:
                files.append(_input_file_row(f"argv[{index}]", candidate))
        configuration = {"argv": definition.get("argv"), "timeout_seconds": definition.get("timeout_seconds"),
                         "max_output_bytes": definition.get("max_output_bytes"), "config": definition.get("config", {})}
        adapters.append({"key": key, "configuration_sha256": _sha256_bytes(_json_bytes(configuration)), "files": files})
    payload = {"modules": modules, "driver_registry": dict(registry_info), "adapters": adapters}
    return {"schema": "shiploop-e2e-verifier-inputs/1", **payload,
            "aggregate_sha256": _sha256_bytes(_json_bytes(payload))}


def _invalidate_executable_passes(rows: dict[str, dict[str, Any]], reason: str) -> None:
    """A source/provenance mutation cannot leave an executable green claim."""
    for check_id, row in rows.items():
        if check_id in REVIEW_OWNED_CHECKS or check_id == "incremental-integration-review":
            continue
        if row.get("status") == "pass":
            rows[check_id] = _row(check_id, "unverified", row.get("evidence", []),
                                  {"reason": reason, "prior_details": row.get("details")})


def _fingerprint_or_error(root: Path) -> dict[str, Any]:
    try:
        return {"available": True, "fingerprint": source_fingerprint(root)}
    except ValueError as exc:
        return {"available": False, "error": type(exc).__name__}


def verify(
    environ: Mapping[str, str], *, drivers_path: Path | None = None, review_path: Path | None = None,
    driver_timeout_seconds: float = DEFAULT_DRIVER_TIMEOUT_SECONDS,
    driver_max_output_bytes: int = DEFAULT_DRIVER_MAX_OUTPUT_BYTES,
) -> dict[str, Any]:
    """Return one artifact-backed receipt; expected shortcomings stay in JSON."""
    if isinstance(driver_timeout_seconds, bool) or not isinstance(driver_timeout_seconds, (int, float)) or not 0 < float(driver_timeout_seconds) <= MAX_DRIVER_TIMEOUT_SECONDS:
        raise ValueError("driver timeout must be positive and within the hard bound")
    if isinstance(driver_max_output_bytes, bool) or not isinstance(driver_max_output_bytes, int) or not 0 < driver_max_output_bytes <= MAX_DRIVER_OUTPUT_BYTES:
        raise ValueError("driver max output bytes must be positive and within the hard bound")
    context = _context(environ)
    step = context["step"]
    evidence = context["evidence"]
    registry, registry_info = load_driver_registry(drivers_path)
    inputs_before = verifier_inputs_manifest(registry, registry_info)
    source_initial = {
        "candidate": _fingerprint_or_error(context["repo"]),
        "baseline": _fingerprint_or_error(context["baseline"]) if context["baseline"].is_dir() else {"available": False, "error": "missing"},
    }
    rows: dict[str, dict[str, Any]] = {
        check_id: _unverified(check_id, "not assessed by this composite verifier")
        for check_id in step["required_checks"]
    }
    mutated_roots: set[str] = set()
    verifier_errors: list[dict[str, str]] = []
    cases: list[dict[str, Any]] = []
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        cases, matrix = _behavior_matrix(
            context, registry, default_timeout=float(driver_timeout_seconds),
            default_maximum=driver_max_output_bytes, mutated_roots=mutated_roots,
        )
        replay_rows, replay_meta = _replay_rows(context, cases, matrix)
        rows.update(replay_rows)
    except (ImportError, KeyError, TypeError, ValueError) as exc:
        failure_path = evidence / "behavior" / "oracle-setup.json"
        _write_json(failure_path, {"schema": TRACE_SCHEMA, "kind": "behavior-oracle-setup",
                                   "status": "unverified", "reason": type(exc).__name__})
        verifier_errors.append({"phase": "behavior", "error": type(exc).__name__})
        replay_meta = {"evidence": [_artifact(evidence, failure_path)], "classification": "unverified"}

    if "gas-compatible-local-artifact" in rows:
        closure = _closure_result(context["repo"], evidence, mutated_roots)
        rows["gas-compatible-local-artifact"] = _row(
            "gas-compatible-local-artifact", closure["status"], closure["evidence"], closure["details"],
        )

    review = _review_assessment(review_path, context)
    for check_id, row in review["owned_rows"].items():
        # Only independent effect/return declarations can fill these rows;
        # review input cannot replace a semantic trace or closure diagnosis.
        if check_id in rows:
            rows[check_id] = row
    if "incremental-integration-review" in rows:
        integration = review["integration"]
        rows["incremental-integration-review"] = _row(
            "incremental-integration-review", integration["status"], integration["evidence"], integration["details"],
        )

    source_final = {
        "candidate": _fingerprint_or_error(context["repo"]),
        "baseline": _fingerprint_or_error(context["baseline"]) if context["baseline"].is_dir() else {"available": False, "error": "missing"},
    }
    source_drift: list[str] = []
    for label in ("candidate", "baseline"):
        before = source_initial[label]
        after = source_final[label]
        if before.get("available") and after.get("available") and before["fingerprint"]["digest"] != after["fingerprint"]["digest"]:
            source_drift.append(label)
            root = context["repo"] if label == "candidate" else context["baseline"]
            mutated_roots.add(str(root.resolve()))
    inputs_after = verifier_inputs_manifest(registry, registry_info)
    input_drift = inputs_after["aggregate_sha256"] != inputs_before["aggregate_sha256"]
    if source_drift:
        _invalidate_executable_passes(rows, "source-drift-during-verification")
    if input_drift:
        _invalidate_executable_passes(rows, "verifier-input-drift-during-verification")
    integrity_path = evidence / "source-integrity.json"
    _write_json(integrity_path, {
        "schema": TRACE_SCHEMA,
        "kind": "source-and-verifier-integrity",
        "source_initial": source_initial,
        "source_final": source_final,
        "source_drift": source_drift,
        "mutated_roots": sorted(mutated_roots),
        "verifier_inputs_before": inputs_before,
        "verifier_inputs_after": inputs_after,
        "verifier_input_drift": input_drift,
    })
    integrity_evidence = [_artifact(evidence, integrity_path)]
    incremental = review["incremental_review"] if context["result"].get("baseline_digest") is not None else {"status": "unverified", "evidence": []}
    return {
        "schema": grading.RECEIPT_SCHEMA,
        "trial_id": context["result"]["trial_id"],
        "candidate_digest": context["result"]["candidate_digest"],
        "baseline_digest": context["result"].get("baseline_digest"),
        "verifier": VERIFIER_SCHEMA,
        "verifier_inputs_sha256": inputs_before["aggregate_sha256"],
        "verifier_inputs": inputs_before,
        "step_id": step["id"],
        "family": context["family"]["id"],
        "driver_registry": registry_info,
        "checks": [rows[check_id] for check_id in step["required_checks"]],
        "incremental_review": incremental,
        "composite": {
            "behavior_case_ids": [case["id"] for case in cases],
            "feature_delta": replay_meta.get("classification", "not-applicable"),
            "source_integrity_evidence": integrity_evidence,
            "review_evidence": review.get("trace_evidence", []),
            "verifier_errors": verifier_errors,
            "source_drift": source_drift,
            "verifier_input_drift": input_drift,
        },
        "limitations": [
            "A semantic adapter is an external read-only observation boundary; its trace does not prove a particular browser implementation.",
            "Local source closure does not prove a hosted Google Apps Script deployment or authorization path.",
            "Reviewer-owned scope, return, and incremental conclusions stay unverified without a matching, pinned independent review.",
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Composite independent verifier for ShipLoop game trials.")
    parser.add_argument("--drivers", type=Path, help="JSON file mapping scenario step/family IDs to bounded adapter argv")
    parser.add_argument("--review", type=Path, help="independent review JSON or per-step review registry")
    parser.add_argument("--driver-timeout", type=float, default=DEFAULT_DRIVER_TIMEOUT_SECONDS)
    parser.add_argument("--max-driver-output-bytes", type=int, default=DEFAULT_DRIVER_MAX_OUTPUT_BYTES)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    receipt = verify(
        dict(os.environ), drivers_path=args.drivers, review_path=args.review,
        driver_timeout_seconds=args.driver_timeout, driver_max_output_bytes=args.max_driver_output_bytes,
    )
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
    # A failed or unverified product belongs in the receipt so the harness's
    # existing grade phase can distinguish it from a verifier execution error.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
