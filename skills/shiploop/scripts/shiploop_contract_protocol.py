"""Protocol adapters for script-owned Ready and Done evidence bindings.

The public result contains observations only. These adapters obtain identities
from the selected run/worktree and retain the check that certified each boundary.
They never perform an external effect or change the active stage themselves.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import shiploop_contracts as contracts
import shiploop_evidence as evidence
import shiploop_knowledge as knowledge
import shiploop_store as store


class ContractGateError(ValueError):
    """The selected step lacks current, intact boundary evidence."""


def enabled(state: dict[str, Any]) -> bool:
    return state.get("step_contract_protocol_version") == contracts.CONTRACT_VERSION


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def environment_identity(root: Path, state: dict[str, Any]) -> str:
    """Bind current-step facts, not unrelated ledger scheduling bookkeeping.

    The complete ledger remains hash-validated. Mapping a future-step obligation
    must not invalidate a current-step proof; changing an applicable observation
    must. Provenance and revision counters are not environmental facts.
    """
    ledger = knowledge.read_bound(root, state)
    step_id = state.get("active_step")
    rows = []
    for row in ledger["entries"]:
        if row.get("scope") != ["all"] and step_id not in row.get("scope", []):
            continue
        rows.append({key: value for key, value in row.items()
                     if key not in ("source", "recorded_revision")})
    rows.sort(key=lambda row: row["id"])
    return _digest({"environment": state.get("environment_sha256", ""), "entries": rows})


def _git(core, worktree: Path, *args: str) -> str:
    result = core.git_run(worktree, *args)
    if result.returncode:
        raise ContractGateError("cannot establish contract Git identity: " + result.stderr.strip())
    return result.stdout.strip()


def _artifact(root: Path, worktree: Path) -> str:
    """Match the verifier's exclusion of the selected durable run directory."""
    try:
        excluded = [str(root.relative_to(worktree))]
    except ValueError:
        excluded = []
    return evidence.fingerprint(worktree, excluded=excluded)


def _require_committed_index(core, worktree: Path) -> None:
    # Worktree hashes alone cannot see a different staged blob whose worktree
    # bytes were restored afterward. Final Done must certify the committed code.
    if _git(core, worktree, "diff", "--cached", "--name-only"):
        raise ContractGateError("Definition of Done has uncommitted staged changes")


def _step(core, root: Path, state: dict[str, Any]) -> dict[str, Any]:
    step = core.steps_by_id(root).get(state.get("active_step"))
    if not isinstance(step, dict):
        raise ContractGateError("no selected step for contract evidence")
    contracts.contract_for_step(step)
    return step


def _check(root: Path, action: str) -> tuple[dict[str, Any], str]:
    if not isinstance(action, str) or not action or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in action):
        raise ContractGateError("unsafe contract check action")
    path = root / "checks" / f"{action}.md"
    if path.is_symlink() or path.parent.is_symlink():
        raise ContractGateError("unsafe contract check path")
    try:
        return store.read_record(path), hashlib.sha256(path.read_bytes()).hexdigest()
    except (store.StorageError, OSError, ValueError) as exc:
        raise ContractGateError("missing or malformed contract check evidence") from exc


def capture(
    core, root: Path, state: dict[str, Any], rec: dict[str, Any],
    payload: Any, *, phase: str, check: dict[str, Any],
) -> dict[str, Any]:
    """Certify Ready before code or Done after current product verification."""
    worktree = Path(rec["worktree"])
    if phase != "ready":
        _require_committed_index(core, worktree)
    action = check["results"]["action_id"]
    persisted, check_digest = _check(root, action)
    if persisted != check:
        raise ContractGateError("contract verification differs from its persisted record")
    normalized = contracts.validate_discharge(
        _step(core, root, state), payload, phase=phase, verify_record=check,
        head=_git(core, worktree, "rev-parse", "HEAD"),
        environment_identity=environment_identity(root, state),
        artifact_identity=_artifact(root, worktree),
    )
    return {
        "step": state["active_step"],
        "evidence": normalized["ready_evidence" if phase == "ready" else "done_evidence"],
        "record": normalized["record"],
        "check_sha256": check_digest,
    }


def require_ready(core, root: Path, state: dict[str, Any], rec: dict[str, Any]) -> None:
    """Keep the issued pre-edit proof intact while authorized code work proceeds.

    Product edits inside the already-issued implement action are expected; they
    are checked at completion, not retroactively treated as pre-edit readiness.
    Environment/contract drift still requires a fresh planning disposition.
    """
    saved = rec.get("contract_ready")
    if not isinstance(saved, dict) or saved.get("step") != state.get("active_step"):
        raise ContractGateError("step requires a pre-edit Definition of Ready certificate")
    envelope = saved.get("record", {}).get("envelope", {})
    check, digest = _check(root, envelope.get("verify_action"))
    if saved.get("check_sha256") != digest:
        raise ContractGateError("Definition of Ready check evidence changed")
    if envelope.get("environment_identity") != environment_identity(root, state):
        raise ContractGateError("Definition of Ready environment changed; replan before continuing")
    if envelope.get("head") != check.get("git_baseline") or envelope.get("artifact_identity") != check.get("worktree_fingerprint"):
        raise ContractGateError("Definition of Ready no longer matches its pre-edit check")
    normalized = contracts.validate_discharge(
        _step(core, root, state), saved.get("evidence"), phase="ready",
        verify_record=check, head=envelope["head"],
        environment_identity=envelope["environment_identity"],
        artifact_identity=envelope["artifact_identity"],
    )
    if normalized["record"] != saved.get("record"):
        raise ContractGateError("Definition of Ready certificate is inconsistent")


def revalidate_done(
    core, root: Path, state: dict[str, Any], rec: dict[str, Any], *, phase: str,
) -> dict[str, Any]:
    """Recheck Done before integration, allowing only proven unchanged-tree audits."""
    saved = rec.get("contract_done")
    if not isinstance(saved, dict) or saved.get("step") != state.get("active_step"):
        raise ContractGateError("step requires a Definition of Done certificate")
    envelope = saved.get("record", {}).get("envelope", {})
    check, digest = _check(root, envelope.get("verify_action"))
    if saved.get("check_sha256") != digest:
        raise ContractGateError("Definition of Done check evidence changed")
    if envelope.get("environment_identity") != environment_identity(root, state):
        raise ContractGateError("Definition of Done environment changed; fresh final verification required")
    worktree = Path(rec["worktree"])
    _require_committed_index(core, worktree)
    head = _git(core, worktree, "rev-parse", "HEAD")
    base = envelope.get("head", "")
    # Query the exact descendant range, never use an LLM-supplied ancestry list.
    if core.git_run(worktree, "merge-base", "--is-ancestor", base, head).returncode:
        raise ContractGateError("Definition of Done audit ancestry changed")
    chain = _git(core, worktree, "rev-list", "--first-parent", f"{base}..{head}").splitlines()
    chain.append(base)
    tree = _git(core, worktree, "rev-parse", f"{base}^{{tree}}")
    for commit in chain:
        if _git(core, worktree, "rev-parse", f"{commit}^{{tree}}") != tree:
            raise ContractGateError("post-verification commits changed the product tree")
    return contracts.validate_discharge(
        _step(core, root, state), saved.get("evidence"), phase=phase,
        verify_record=check, head=head, environment_identity=environment_identity(root, state),
        artifact_identity=_artifact(root, worktree),
        certified_rebind={
            "certified_head": base,
            "certified_artifact_identity": envelope.get("artifact_identity"),
            "certified_verify_action": envelope.get("verify_action"),
            "certified_contract_sha256": envelope.get("contract_sha256"),
            "ancestry": chain,
        },
    )
