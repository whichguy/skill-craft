"""Nonmutating recovery context for the repository E2E harness.

Inspection never records a run choice or invokes a recovery-capable workspace
operation. A verified binding identifies a checkout; it certifies no obligation.
"""
from __future__ import annotations

from pathlib import Path
import run_choice
import runrecord
import shiploop_store as store
import shiploop_workspace as workspace


def inspect_context(out: Path, phase: str) -> dict:
    result = {"schema": "shiploop-e2e-recovery-context/1", "status": "UNKNOWN",
              "phase": phase, "source": None, "binding": None, "selected_run": None,
              "inspector": {"implementation": str(Path(__file__).resolve())},
              "scope": "checkout-binding-only", "launches": [], "unreadable_launches": []}

    def unresolved(reason):
        result["reason"] = reason
        return result

    try:
        if phase not in {"builder", "final"}:
            return unresolved("unsupported-phase")
        out = Path(out)
        if out.is_symlink() or not out.is_dir():
            return unresolved("unsafe-output-directory")
        out = out.resolve()
        result["output"] = str(out)
        result["unreadable_launches"] = runrecord.unreadable(out)
        launches = runrecord.launches(out)
        result["launches"] = [{"file": name, "recorded": record} for name, record in launches]
        choice = run_choice.choose(out)
        result["selection_basis"] = choice.basis
        result["candidates"] = choice.mine
        if choice.chosen is None:
            return unresolved("ambiguous-runs" if choice.tied else "missing-run")
        result["selected_run"] = choice.chosen
        if (result["unreadable_launches"] or not launches
                or any((out / name).is_symlink() for name, _ in launches)):
            return unresolved("launch-provenance-unresolved")
        run_dir = Path(choice.chosen["run_dir"])
        if run_dir.resolve() != run_dir or not run_dir.is_relative_to(out):
            return unresolved("unsafe-run-directory")
        if (run_dir / "state.md").is_symlink():
            return unresolved("unsafe-run-state")
        state_bytes = (run_dir / "state.md").read_bytes()
        state = store.read_record(run_dir / "state.md")
        repo = Path(state["repo"])
        observed = workspace.binding_snapshot(run_dir.parent, repo)
        if observed is None:
            return unresolved("workspace-binding-unresolved")
        manifest = observed["manifest"]
        if manifest["run_dir"] != str(run_dir) or manifest["worktree"] != str(repo):
            return unresolved("selected-run-binding-mismatch")
        source = Path(manifest["source_repo"])
        if any(record.get("cwd") != str(source) for _, record in launches):
            return unresolved("launch-source-mismatch")
        case = launches[0][1].get("case")
        if not isinstance(case, str) or any(record.get("case") != case for _, record in launches):
            return unresolved("launch-case-unresolved")
        result["case"] = case
        current = repo
        kind = "active-execution"
        head = observed["execution_head"]
        if phase == "final":
            receipt = workspace.completed_receipt_snapshot(run_dir.parent, source)
            if receipt is None:
                return unresolved("completed-return-unresolved")
            current, kind, head = source, "verified-return", observed["source_head"]
        if (workspace.binding_snapshot(run_dir.parent, repo) != observed
                or (run_dir / "state.md").read_bytes() != state_bytes
                or run_choice.choose(out).chosen != choice.chosen
                or runrecord.launches(out) != launches or runrecord.unreadable(out)):
            return unresolved("context-changed-during-inspection")
        # Binding permits dirty builder files; only receipt validation checks returned content.
        if phase == "final" and workspace.completed_receipt_snapshot(run_dir.parent, source) != receipt:
            return unresolved("completed-return-changed-during-inspection")
        result.update(status="resolved", reason=None,
                      source={"repo": str(current), "head": head},
                      binding={"kind": kind, "workspace_root": str(run_dir.parent),
                               "manifest": str(run_dir.parent / "workspace.md"),
                               "source_repo": str(source), "execution_worktree": str(repo),
                               "run_dir": str(run_dir), "common_dir": observed["common_dir"]})
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, store.StorageError, workspace.WorkspaceError):
        return unresolved("context-unreadable-or-unsupported")
