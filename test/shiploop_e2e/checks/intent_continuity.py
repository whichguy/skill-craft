#!/usr/bin/env python3
"""Independent byte-identity oracle for ShipLoop's current-spec lifecycle.

This checks run records and Git trees only. It does not import ShipLoop's
runtime or assess semantic preservation, delta-only plans, causal retrieval, or
every intermediate write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "shiploop-intent-continuity-v1"
STATE_VERSION = 12
CURRENT_SPEC = "current-spec.md"
AGGREGATE = "docs/shiploop/spec.md"
SNAPSHOTS = {
    "spec": (AGGREGATE, "spec/prior-spec.md"),
    "architecture": ("docs/shiploop/architecture.md", "spec/prior-architecture.md"),
    "environment": ("docs/shiploop/environment.md", "spec/prior-environment.md"),
}
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
SHA = re.compile(r"^[0-9a-f]{40,64}$")
ACTION = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")


class OracleError(ValueError):
    """Evidence is missing, unsafe, or does not match the accepted identity."""


class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def pass_(self, check: str, observed: Any) -> None:
        self.items.append({"check": check, "pass": True, "observed": observed})

    def require(self, check: str, condition: bool, detail: str, observed: Any = None) -> None:
        if not condition:
            self.items.append({"check": check, "pass": False, "observed": observed, "detail": detail})
            raise OracleError(detail)
        self.pass_(check, observed if observed is not None else detail)


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OracleError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise OracleError(f"non-standard JSON constant: {value}")


def _decode_json(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_json_pairs,
                          parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OracleError(f"{label} is not valid UTF-8 JSON: {exc}") from exc


def _fenced_record(path: Path, root: Path, *, required: bool = True) -> dict[str, Any] | None:
    raw = _read_file(root, path.relative_to(root).as_posix(), required=required)
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OracleError(f"{path} is not valid UTF-8: {exc}") from exc
    lines = [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]
    openings = [index for index, line in enumerate(lines) if line == "```shiploop-state"]
    if any(line.startswith("```shiploop-state") and line != "```shiploop-state" for line in lines):
        raise OracleError(f"{path} has a malformed shiploop-state fence")
    if len(openings) != 1:
        raise OracleError(f"{path} must contain exactly one shiploop-state JSON fence")
    start = openings[0] + 1
    end = next((index for index in range(start, len(lines))
                if re.fullmatch(r"```[ \t]*", lines[index])), None)
    if end is None:
        raise OracleError(f"{path} has an unterminated shiploop-state fence")
    value = _decode_json("\n".join(lines[start:end]).encode("utf-8"), str(path))
    if not isinstance(value, dict):
        raise OracleError(f"{path} shiploop-state payload must be an object")
    return value


def _read_file(root: Path, relative: str, *, required: bool = True) -> bytes | None:
    if (not relative or "\x00" in relative or "\\" in relative or relative.startswith("/")
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise OracleError(f"unsafe record path: {relative!r}")
    current = root
    parts = relative.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if required:
                raise OracleError(f"required file is missing: {current}")
            return None
        except OSError as exc:
            raise OracleError(f"cannot inspect {current}: {exc}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise OracleError(f"symlink is not allowed in evidence path: {current}")
        if index < len(parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                raise OracleError(f"evidence parent is not a directory: {current}")
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OracleError(f"evidence file must be a private regular file: {current}")
    try:
        return current.read_bytes()
    except OSError as exc:
        raise OracleError(f"cannot read {current}: {exc}") from exc


def _absolute_dir(value: str | Path, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise OracleError(f"{label} must be a canonical absolute path")
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise OracleError(f"{label} does not resolve: {candidate}: {exc}") from exc
    if resolved != candidate or not resolved.is_dir():
        raise OracleError(f"{label} must be an existing non-symlink directory: {candidate}")
    return resolved


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return path != parent
    except ValueError:
        return False


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    for key in list(env):
        if key in {
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
        } or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(key, None)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0",
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_REPLACE_OBJECTS": "1"})
    try:
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                              env=env, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise OracleError(f"Git evidence command failed: {type(exc).__name__}") from exc


def _git_text(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise OracleError(f"git {' '.join(args[:2])} failed" + (f": {message[-1]}" if message else ""))
    return result.stdout.decode("utf-8", "surrogateescape").strip()


def _check_object(repo: Path, object_id: str, kind: str) -> None:
    if not isinstance(object_id, str) or SHA.fullmatch(object_id) is None:
        raise OracleError(f"invalid Git {kind} object ID")
    actual = _git_text(repo, "cat-file", "-t", object_id)
    if actual != kind:
        raise OracleError(f"Git object {object_id} is {actual}, expected {kind}")


def _git_blob(repo: Path, tree: str, relative: str) -> bytes | None:
    _check_object(repo, tree, "tree")
    expression = f"{tree}:{relative}"
    exists = _git(repo, "ls-tree", "-z", tree, "--", relative)
    if exists.returncode:
        detail = exists.stderr.decode("utf-8", "replace").strip().splitlines()
        raise OracleError("cannot inspect Git path " + relative + (f": {detail[-1]}" if detail else ""))
    if not exists.stdout:
        return None
    result = _git(repo, "show", expression)
    if result.returncode:
        raise OracleError(f"cannot read Git path {relative} from {tree}")
    return result.stdout


def _tree_for_return(receipt: Mapping[str, Any]) -> str:
    kind = receipt.get("kind")
    expected = receipt.get("expected_source")
    if not isinstance(expected, dict):
        raise OracleError("return receipt has no expected_source object")
    key = "tree" if kind == "fast-forward-merge" else "working_tree"
    if kind not in {"fast-forward-merge", "working-tree-return", "no-change-return"}:
        raise OracleError("return receipt has an unsupported kind")
    tree = expected.get(key)
    if not isinstance(tree, str) or SHA.fullmatch(tree) is None:
        raise OracleError(f"return receipt expected_source has no valid {key}")
    return tree


def _head_for_return(receipt: Mapping[str, Any]) -> str:
    expected = receipt.get("expected_source")
    head = expected.get("head") if isinstance(expected, dict) else None
    if not isinstance(head, str) or SHA.fullmatch(head) is None:
        raise OracleError("return receipt expected_source has no valid head")
    return head


def _receipt_chain(final: dict[str, Any]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current: Any = final
    while isinstance(current, dict):
        if (current.get("schema") != "shiploop-workspace-return-receipt"
                or type(current.get("version")) is not int or current.get("version") != 1):
            raise OracleError("return receipt chain has an unsupported format")
        if current.get("status") != "returned":
            raise OracleError("return receipt chain contains an incomplete return")
        chain.append(current)
        previous = current.get("previous_receipt")
        if previous is None:
            break
        if not isinstance(previous, dict):
            raise OracleError("previous_receipt must be a nested receipt object")
        current = previous
    return list(reversed(chain))


def _same_source_tree(source: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    expected = receipt.get("expected_source")
    if not isinstance(expected, dict):
        return False
    head = source.get("head")
    expected_head = expected.get("head")
    if head != expected_head:
        return False
    tree_key = "tree" if "tree" in expected else "working_tree"
    return source.get(tree_key) == expected.get(tree_key)


def _run_record_checks(mode: str, checks: Findings) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
    cwd = _absolute_dir(Path.cwd(), "product cwd")
    output = _absolute_dir(cwd.parent, "output directory")
    marker_raw = _read_file(output, "shiploop-run.json")
    marker = _decode_json(marker_raw or b"", "shiploop-run.json")
    if not isinstance(marker, dict) or not isinstance(marker.get("run_dir"), str):
        raise OracleError("shiploop-run.json must select one absolute run_dir")
    run_dir = _absolute_dir(marker["run_dir"], "selected run directory")
    if not _inside(run_dir, output):
        raise OracleError("selected run_dir must be contained by the output directory")
    if mode == "worktree" and run_dir.name != "run":
        raise OracleError("worktree run_dir must be named run beneath its bound workspace root")
    invocation_raw = _read_file(output, "invocation.json")
    metrics_raw = _read_file(output, "metrics.json")
    invocation = _decode_json(invocation_raw or b"", "invocation.json")
    metrics = _decode_json(metrics_raw or b"", "metrics.json")
    if not isinstance(invocation, dict) or not isinstance(metrics, dict):
        raise OracleError("invocation.json and metrics.json must contain objects")
    checks.pass_("selected-run", {"output": str(output), "run_dir": str(run_dir),
                                   "invocation": "present", "metrics": "present"})
    return cwd, output, run_dir, invocation, metrics


def _identity_and_spec(mode: str, cwd: Path, run_dir: Path,
                       invocation: Mapping[str, Any], checks: Findings) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes | None]:
    state = _fenced_record(run_dir / "state.md", run_dir)
    if state is None:
        raise OracleError("selected run state is missing")
    version = state.get("version")
    if type(version) is not int or version != STATE_VERSION:
        raise OracleError(f"run state version {version!r} lacks intent-continuity capability; requires version 12")
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or ACTION.fullmatch(run_id) is None:
        raise OracleError("run state has an unsafe or missing run_id")
    if state.get("status") != "done":
        raise OracleError("selected ShipLoop run has not reached done")
    if state.get("spec_root") != str(run_dir):
        raise OracleError("state spec_root does not match the selected run_dir")

    if mode == "worktree":
        root = run_dir.parent
        workspace = _fenced_record(root / "workspace.md", root)
        if workspace is None:
            raise OracleError("worktree mode is missing workspace.md")
        worktree = _absolute_dir(root / "worktree", "workspace worktree")
        if (workspace.get("schema") != "shiploop-workspace"
                or type(workspace.get("version")) is not int or workspace.get("version") != 1
                or workspace.get("status") != "returned" or workspace.get("source_repo") != str(cwd)
                or workspace.get("run_dir") != str(run_dir) or workspace.get("worktree") != str(worktree)):
            raise OracleError("workspace manifest identity does not match the selected run and delivered repo")
        expected_repo = worktree
    else:
        expected_repo = cwd
        # A direct run has no workspace wrapper or return receipt at the selected run's parent.
        for rel in ("workspace.md", "return-receipt.md"):
            if _read_file(run_dir.parent, rel, required=False) is not None:
                raise OracleError(f"direct mode contains fabricated workspace evidence: {rel}")

    repo_value = state.get("repo")
    if repo_value != str(expected_repo):
        raise OracleError("state repo does not match the selected execution repo")
    binding = _fenced_record(run_dir / "spec" / "binding.md", run_dir)
    candidate = _read_file(run_dir, CURRENT_SPEC)
    if binding is None or candidate is None:
        raise OracleError("current-spec binding or candidate is missing")
    try:
        candidate_text = candidate.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OracleError("current-spec candidate is not valid UTF-8") from exc
    if not candidate_text.strip():
        raise OracleError("current-spec candidate is blank")
    expected_binding_keys = {"schema", "version", "run_id", "repo", "root", "candidate",
                             "candidate_initial_sha256", "snapshots"}
    if (set(binding) != expected_binding_keys or binding.get("schema") != "shiploop-current-spec"
            or type(binding.get("version")) is not int or binding.get("version") != 1
            or binding.get("run_id") != run_id
            or binding.get("repo") != str(expected_repo) or binding.get("root") != str(run_dir)
            or binding.get("candidate") != CURRENT_SPEC):
        raise OracleError("current-spec binding identity or candidate path does not match this run")
    current_hash = hashlib.sha256(candidate).hexdigest()
    prior_spec = _validate_snapshots(run_dir, expected_repo, binding, invocation, checks)
    checks.require("run-state", True, "v12 selected run reached done",
                   {"run_id": run_id, "version": version, "repo": str(expected_repo), "root": str(run_dir)})
    checks.require("current-spec-binding", True, "run_id/repo/root bind current-spec.md",
                   {"candidate": CURRENT_SPEC, "sha256": current_hash})
    return state, binding, candidate, prior_spec


def _validate_snapshots(run_dir: Path, repo: Path, binding: Mapping[str, Any],
                        invocation: Mapping[str, Any], checks: Findings) -> bytes | None:
    snapshots = binding.get("snapshots")
    if not isinstance(snapshots, dict) or set(snapshots) != set(SNAPSHOTS):
        raise OracleError("current-spec binding must include spec, architecture, and environment snapshots")
    spec_entry = snapshots.get("spec")
    expected_initial = (spec_entry.get("sha256") if isinstance(spec_entry, dict) and spec_entry.get("present")
                        else EMPTY_SHA256)
    if binding.get("candidate_initial_sha256") != expected_initial:
        raise OracleError("current-spec initial candidate digest does not match the prior spec snapshot")
    prior_spec: bytes | None = None
    for name, (_source_path, snapshot_path) in SNAPSHOTS.items():
        entry = snapshots.get(name)
        if (not isinstance(entry, dict) or set(entry) != {"path", "present", "sha256"}
                or entry.get("path") != snapshot_path or type(entry.get("present")) is not bool):
            raise OracleError(f"current-spec binding has malformed {name} snapshot metadata")
        actual = _read_file(run_dir, snapshot_path, required=False)
        present = entry["present"]
        digest = entry.get("sha256")
        if present:
            if actual is None or not isinstance(digest, str) or hashlib.sha256(actual).hexdigest() != digest:
                raise OracleError(f"prior {name} snapshot bytes do not match the binding digest")
            try:
                actual.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise OracleError(f"prior {name} snapshot is not UTF-8") from exc
        elif actual is not None or digest is not None:
            raise OracleError(f"absent prior {name} snapshot unexpectedly has bytes or a digest")
        if name == "spec":
            prior_spec = actual

    follow_on = invocation.get("follow_on")
    if follow_on is None:
        if snapshots["spec"].get("present") or prior_spec is not None:
            raise OracleError("new-root run must have no prior aggregate spec")
        if binding.get("candidate_initial_sha256") != EMPTY_SHA256:
            raise OracleError("new-root candidate did not start from the empty spec")
        checks.pass_("prior-spec", {"mode": "new-root", "present": False, "sha256": EMPTY_SHA256})
    else:
        if not isinstance(follow_on, dict):
            raise OracleError("invocation.follow_on must be an object when present")
        start = follow_on.get("start_head")
        if not isinstance(start, str) or SHA.fullmatch(start) is None:
            raise OracleError("invocation.follow_on.start_head is not a full Git object ID")
        _check_object(repo, start, "commit")
        for name, (source_path, _snapshot_path) in SNAPSHOTS.items():
            expected = _git_blob(repo, _git_text(repo, "rev-parse", f"{start}^{{tree}}"), source_path)
            snapshot = _read_file(run_dir, SNAPSHOTS[name][1], required=False)
            if expected != snapshot:
                raise OracleError(f"prior {name} snapshot differs from invocation.follow_on.start_head")
        checks.pass_("prior-spec", {"mode": "follow-on", "start_head": start,
                                     "sha256": hashlib.sha256(prior_spec).hexdigest() if prior_spec is not None else EMPTY_SHA256})
    return prior_spec


def _review_and_promotion(run_dir: Path, state: Mapping[str, Any], binding: Mapping[str, Any],
                          candidate: bytes, prior: bytes | None, checks: Findings) -> None:
    reviewed = _fenced_record(run_dir / "spec" / "reviewed.md", run_dir)
    if reviewed is None:
        raise OracleError("accepted current-spec review is missing")
    current_hash = hashlib.sha256(candidate).hexdigest()
    run_id, repo, root = binding["run_id"], binding["repo"], binding["root"]
    action = reviewed.get("action")
    accepted = state.get("accepted")
    improve_results = state.get("improve_results")
    item = accepted.get(action) if isinstance(accepted, dict) and isinstance(action, str) else None
    if (reviewed.get("schema") != "shiploop-spec-reviewed-v1" or reviewed.get("run_id") != run_id
            or reviewed.get("repo") != repo or reviewed.get("root") != root
            or reviewed.get("sha256") != current_hash or not isinstance(action, str)
            or not isinstance(item, dict) or item.get("outcome") != "done"
            or not isinstance(improve_results, dict) or action not in improve_results):
        raise OracleError("reviewed.md does not bind the exact current bytes to an accepted completed Improve")
    checks.pass_("accepted-improve-review", {"action": action, "sha256": current_hash})

    promotion = _fenced_record(run_dir / "spec" / "promotion.md", run_dir, required=False)
    if promotion is None:
        raise OracleError("terminal spec promotion is missing")
    handoff = promotion.get("handoff_action")
    handoff_item = accepted.get(handoff) if isinstance(accepted, dict) and isinstance(handoff, str) else None
    history = state.get("history")
    accepted_handoff = (isinstance(history, list) and any(
        isinstance(row, dict) and row.get("action") == handoff and row.get("stage") == "handoff"
        and row.get("outcome") == "done" for row in history))
    prior_hash = hashlib.sha256(prior).hexdigest() if prior is not None else EMPTY_SHA256
    keys = {"schema", "version", "status", "run_id", "repo", "root", "handoff_action",
            "aggregate", "candidate", "candidate_sha256", "current_sha256", "prior_sha256",
            "prior_present", "summary"}
    if (set(promotion) != keys or promotion.get("schema") != "shiploop-spec-promotion"
            or type(promotion.get("version")) is not int or promotion.get("version") != 1
            or promotion.get("status") != "promoted"
            or promotion.get("run_id") != run_id or promotion.get("repo") != repo
            or promotion.get("root") != root or not isinstance(handoff, str) or ACTION.fullmatch(handoff) is None
            or not isinstance(handoff_item, dict) or handoff_item.get("outcome") != "done"
            or not accepted_handoff or promotion.get("aggregate") != AGGREGATE
            or promotion.get("candidate") != CURRENT_SPEC or promotion.get("candidate_sha256") != current_hash
            or promotion.get("current_sha256") != current_hash or promotion.get("prior_sha256") != prior_hash
            or promotion.get("prior_present") is not (prior is not None)):
        raise OracleError("promotion.md is not the promoted record for this run's accepted handoff and exact hashes")
    checks.pass_("accepted-handoff-promotion", {"handoff_action": handoff, "status": "promoted",
                                                  "current_sha256": current_hash,
                                                  "prior_sha256": prior_hash})


def _delivered_bytes(cwd: Path, repo: Path, candidate: bytes, checks: Findings) -> None:
    for label, root in (("delivered", cwd), ("execution", repo)):
        raw = _read_file(root, AGGREGATE)
        if raw != candidate:
            raise OracleError(f"{label} {AGGREGATE} bytes do not exactly match current-spec.md")
    checks.pass_("delivered-spec-bytes", {"path": AGGREGATE, "sha256": hashlib.sha256(candidate).hexdigest(),
                                           "delivered_and_execution_match": True})


def _workspace_return(cwd: Path, run_dir: Path, candidate: bytes,
                      prior: bytes | None, checks: Findings) -> None:
    root = run_dir.parent
    receipt = _fenced_record(root / "return-receipt.md", root)
    if receipt is None:
        raise OracleError("worktree return-receipt.md is missing")
    chain = _receipt_chain(receipt)
    if len(chain) < 2:
        raise OracleError("worktree mode lacks an observed follow-up return receipt")

    for index, entry in enumerate(chain):
        tree = _tree_for_return(entry)
        head = _head_for_return(entry)
        _check_object(cwd, head, "commit")
        actual_spec = _git_blob(cwd, tree, AGGREGATE)
        expected_spec = prior if index < len(chain) - 1 else candidate
        if actual_spec != expected_spec:
            label = "prior aggregate" if index < len(chain) - 1 else "promoted candidate"
            raise OracleError(f"returned tree {index + 1} does not preserve the exact {label} bytes")
        source_before = entry.get("source_before")
        if not isinstance(source_before, dict):
            raise OracleError("return receipt has no source_before fingerprint")
        if index == 0:
            before_tree = source_before.get("working_tree")
            if not isinstance(before_tree, str) or SHA.fullmatch(before_tree) is None:
                raise OracleError("first return has no valid source_before working_tree")
            before_spec = _git_blob(cwd, before_tree, AGGREGATE)
            if before_spec != prior:
                raise OracleError("first return source_before does not contain the exact prior aggregate")
        elif not _same_source_tree(source_before, chain[index - 1]):
            raise OracleError("return receipt source_before does not match its previous returned tree")

    # The final receipt must be the state currently delivered in this checkout.
    final = chain[-1]
    final_head, final_tree = _head_for_return(final), _tree_for_return(final)
    current_head = _git_text(cwd, "rev-parse", "HEAD")
    if final_head != current_head:
        raise OracleError("final return receipt head does not match the delivered Git HEAD")
    kind = final.get("kind")
    if kind == "fast-forward-merge":
        current_tree = _git_text(cwd, "rev-parse", "HEAD^{tree}")
        status = _git(cwd, "status", "--porcelain=v1", "--untracked-files=all")
        if final_tree != current_tree or status.returncode or status.stdout:
            raise OracleError("final fast-forward return tree does not match the clean delivered Git tree")
    else:
        diff = _git(cwd, "diff", "--no-ext-diff", "--quiet", final_tree, "--")
        if diff.returncode != 0:
            raise OracleError("final returned working_tree does not match delivered tracked files")

    previous_tree = _tree_for_return(chain[-2])
    changes = _git(cwd, "diff", "--name-only", "-z", "--no-renames", previous_tree, final_tree)
    if changes.returncode:
        raise OracleError("cannot inspect final follow-up tree delta")
    names = [part.decode("utf-8", "surrogateescape") for part in changes.stdout.split(b"\0") if part]
    if AGGREGATE not in names or any(not path.startswith("docs/shiploop/") for path in names):
        raise OracleError("final worktree receipt is not an observed knowledge-only docs/shiploop follow-up")
    checks.pass_("worktree-return-chain", {"receipts": len(chain), "final_head": final_head,
                                            "final_tree": final_tree, "follow_up_paths": names})


def _direct_mode(cwd: Path, run_dir: Path, checks: Findings) -> None:
    if _read_file(run_dir.parent, "workspace.md", required=False) is not None:
        raise OracleError("direct mode has a fabricated workspace manifest")
    if _read_file(run_dir.parent, "return-receipt.md", required=False) is not None:
        raise OracleError("direct mode has a fabricated workspace return receipt")
    checks.pass_("direct-execution", {"repo": str(cwd), "workspace_return": "absent"})


def evaluate(mode: str) -> tuple[dict[str, Any], int]:
    checks = Findings()
    try:
        cwd, _output, run_dir, invocation, _metrics = _run_record_checks(mode, checks)
        state, binding, candidate, prior = _identity_and_spec(mode, cwd, run_dir, invocation, checks)
        repo = Path(state["repo"])
        _review_and_promotion(run_dir, state, binding, candidate, prior, checks)
        _delivered_bytes(cwd, repo, candidate, checks)
        if mode == "worktree":
            _workspace_return(cwd, run_dir, candidate, prior, checks)
        else:
            _direct_mode(cwd, run_dir, checks)
        result = {"schema": SCHEMA, "mode": mode, "pass": True, "findings": checks.items,
                  "limitations": ["Checks lifecycle and byte identities only; it does not assess semantic preservation, "
                                  "delta-only plans, causal retrieval, or every intermediate write."]}
        return result, 0
    except Exception as exc:
        detail = str(exc) if isinstance(exc, OracleError) else f"{type(exc).__name__}: {exc}"
        if not checks.items or checks.items[-1].get("pass") is not False:
            checks.items.append({"check": "oracle", "pass": False, "detail": detail})
        return {"schema": SCHEMA, "mode": mode, "pass": False, "findings": checks.items,
                "limitations": ["Checks lifecycle and byte identities only; it does not assess semantic preservation, "
                                "delta-only plans, causal retrieval, or every intermediate write."]}, 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("worktree", "direct"), required=True)
    args = parser.parse_args(argv)
    payload, code = evaluate(args.mode)
    print(json.dumps(payload, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
