"""The prepare phase's scoped commit boundary.

The first prepare packet records the Git state after earlier stage effects have
finished. A done result may then authorize exact files that changed from that
entry and were clean at entry. This is path-scoped authority, not proof of who
made a concurrent same-path edit. Knowledge-home changes remain with their
existing, later close.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import shiploop_git
import shiploop_item_scope as item_scope
import shiploop_lint as lint
import shiploop_store as store

RECORD_FILE = "preparation.md"
SCHEMA = "shiploop-preparation/v1"
_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_RESULT_SHA256 = re.compile(r"[0-9a-f]{64}")
_KNOWLEDGE_HOME = "docs/shiploop"
_MESSAGE = "chore(shiploop): commit declared preparation paths"


class PreparationError(RuntimeError):
    """Preparation ownership or its pending commit cannot be trusted."""


class PendingPreparationError(PreparationError):
    """The exact pending callback cannot be recovered or validated."""


def record_path(run_dir: Path) -> Path:
    """The one durable entry/pending record for a run's prepare phase."""
    return Path(run_dir) / RECORD_FILE


def normalise_paths(value: Any) -> list[str]:
    """Validate concrete repository-relative file names; wildcard characters are literal filename characters."""
    if not isinstance(value, list):
        raise PreparationError("prepare paths must be a list of concrete repository-relative file paths")
    rows: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry or "\n" in entry or "\r" in entry or "\0" in entry:
            raise PreparationError("each prepare path must be one nonblank repository-relative file path")
        path = entry
        if path.startswith("./"):
            path = path[2:]
        parts = path.split("/")
        if (not path or path.startswith(("/", "\\\\")) or re.match(r"^[A-Za-z]:[/\\]", path)
                or any(part in ("", ".", "..") for part in parts)
                or path.endswith("/")):
            raise PreparationError("prepare paths must be concrete files inside the repository: " + entry)
        rows.append(path)
    if len(set(rows)) != len(rows):
        raise PreparationError("prepare paths must not repeat")
    return rows


def _result_sha256(value: Any) -> str:
    """Digest one canonical accepted producer result using stable sorted compact JSON."""
    if not isinstance(value, Mapping):
        raise PreparationError("the accepted preparation result is not an object")
    try:
        raw = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PreparationError("the accepted preparation result is not JSON-safe") from exc
    return hashlib.sha256(raw).hexdigest()


def _pending_result_error(run_dir: Path, reason: str) -> PendingPreparationError:
    return PendingPreparationError(
        reason + ". Restore the exact original canonical callback result from "
        + str(record_path(run_dir)) + " under pending.result, then retry the same callback; no stage was advanced")


def _read_record(run_dir: Path) -> dict[str, Any] | None:
    path = record_path(run_dir)
    if path.is_symlink():
        raise PreparationError("the preparation record is a symlink; ownership is unknown")
    if not path.exists():
        return None
    if not path.is_file():
        raise PreparationError("the preparation record is not a regular file; ownership is unknown")
    try:
        value = store.read_record(path)
    except (OSError, store.StorageError) as exc:
        raise PreparationError("the preparation record cannot be read; ownership is unknown") from exc
    if not isinstance(value, Mapping) or value.get("schema") != SCHEMA:
        raise PreparationError("the preparation record is invalid; ownership is unknown")
    record = dict(value)
    if (record.get("status") not in ("ready", "unknown")
            or not all(isinstance(record.get(key), str) and record.get(key)
                       for key in ("run_id", "run_dir", "repo", "execution_mode", "entry_action"))
            or not isinstance(record.get("lineage"), list)
            or not all(isinstance(action, str) and action for action in record["lineage"])
            or record.get("entry_action") not in record["lineage"]):
        raise PreparationError("the preparation record is invalid; ownership is unknown")
    if record["status"] == "ready":
        if (not _OBJECT_ID.fullmatch(str(record.get("entry_head") or ""))
                or not _OBJECT_ID.fullmatch(str(record.get("head_tree") or ""))
                or not _OBJECT_ID.fullmatch(str(record.get("entry_tree") or ""))
                or not isinstance(record.get("toplevel"), str) or not Path(record["toplevel"]).is_absolute()
                or not isinstance(record.get("prefix"), str)
                or not isinstance(record.get("dirty_paths"), list)
                or not all(isinstance(path, str) for path in record["dirty_paths"])
                or not isinstance(record.get("ignored_paths"), list)
                or not all(isinstance(path, str) for path in record["ignored_paths"])):
            raise PreparationError("the preparation entry record is invalid; ownership is unknown")
        pending = record.get("pending")
        if pending is not None and (not isinstance(pending, Mapping)
                or pending.get("action") not in record["lineage"]
                or not _OBJECT_ID.fullmatch(str(pending.get("parent") or ""))
                or not _OBJECT_ID.fullmatch(str(pending.get("tree") or ""))
                or not isinstance(pending.get("paths"), list)
                or not all(isinstance(path, str) for path in pending["paths"])
                or not isinstance(pending.get("message"), str)
                or not isinstance(pending.get("result"), Mapping)
                or not isinstance(pending.get("result_sha256"), str)
                or not _RESULT_SHA256.fullmatch(pending["result_sha256"])):
            raise _pending_result_error(
                Path(run_dir), "the pending preparation record is missing its original result binding")
        if pending is not None:
            try:
                saved_result_sha = _result_sha256(pending["result"])
            except PreparationError as exc:
                raise _pending_result_error(Path(run_dir), "the pending preparation result is invalid") from exc
            if saved_result_sha != pending["result_sha256"]:
                raise _pending_result_error(
                    Path(run_dir), "the pending preparation result digest does not match its saved result")
            try:
                pending_paths = normalise_paths(pending["paths"])
            except PreparationError as exc:
                raise _pending_result_error(Path(run_dir), "the pending preparation paths are invalid") from exc
            if not pending_paths or pending_paths != pending["paths"]:
                raise _pending_result_error(Path(run_dir), "the pending preparation paths are invalid")
            if pending.get("parent") != record.get("entry_head"):
                raise _pending_result_error(Path(run_dir),
                                            "the pending preparation commit is not on the saved prepare-entry HEAD")
    return record


def _write_record(run_dir: Path, record: Mapping[str, Any]) -> None:
    path = record_path(run_dir)
    if path.is_symlink():
        raise PreparationError("the preparation record is a symlink; ownership is unknown")
    if path.exists() and not path.is_file():
        raise PreparationError("the preparation record is not a regular file; ownership is unknown")
    try:
        store.write_record(path, dict(record), "ShipLoop prepare ownership")
    except (OSError, store.StorageError) as exc:
        raise PreparationError("cannot persist the preparation ownership record") from exc


def _identity(run_dir: Path, state: Mapping[str, Any]) -> dict[str, str]:
    repo = Path(str(state.get("repo") or ""))
    run_id = state.get("run_id")
    run = Path(run_dir)
    if (run.is_symlink() or not run.is_absolute() or not repo.is_absolute()
            or not isinstance(run_id, str) or not run_id):
        raise PreparationError("the preparation phase has no bound run and repository identity")
    return {"run_id": run_id, "run_dir": os.path.realpath(os.fspath(run)),
            "repo": os.path.realpath(os.fspath(repo)),
            "execution_mode": str(state.get("execution_mode") or "")}


def _lineage(state: Mapping[str, Any], action_id: str) -> list[str]:
    actions = [str(row.get("action")) for row in state.get("history", ())
               if isinstance(row, Mapping) and row.get("stage") == "prepare" and row.get("action")]
    if action_id not in actions:
        actions.append(action_id)
    return list(dict.fromkeys(actions))


def _packet_recorded(run_dir: Path, action_id: str) -> bool:
    """Trace is evidence that an action was issued; unreadable trace state is treated conservatively."""
    path = Path(run_dir) / "trace.jsonl"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return True
    if not path.exists():
        return False
    try:
        events = store.read_jsonl(path)
    except (OSError, store.StorageError):
        return True
    return any(row.get("kind") == "packet" and row.get("stage") == "prepare"
               and row.get("action") == action_id for row in events if isinstance(row, Mapping))


def _dirty_paths(top: Path, prefix: str) -> list[str]:
    """Every dirty path, including staged-only entries; porcelain -z keeps names lossless and unquoted."""
    status = lint._git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status.returncode:
        raise PreparationError("cannot read prepare-entry dirty paths")
    raw = status.stdout.split(b"\0")
    names: list[bytes] = []
    index = 0
    while index < len(raw):
        row = raw[index]
        index += 1
        if not row:
            continue
        if len(row) < 4 or row[2:3] != b" ":
            raise PreparationError("Git returned an unreadable prepare-entry status record")
        names.append(row[3:])
        if b"R" in row[:2] or b"C" in row[:2]:
            if index < len(raw) and raw[index]:
                names.append(raw[index])
                index += 1
    lead = "" if prefix in ("", ".") else prefix.rstrip("/") + "/"
    result = {name.decode("utf-8", "surrogateescape")[len(lead):]
              for name in names
              if name.decode("utf-8", "surrogateescape").startswith(lead)}
    return sorted(result)


def _ignored_paths(top: Path, prefix: str) -> list[str]:
    """Ignored untracked files are outside the snapshot too; retain their entry roots across ignore-rule changes."""
    listed = lint._git(top, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z")
    if listed.returncode:
        raise PreparationError("cannot read prepare-entry ignored paths")
    lead = "" if prefix in ("", ".") else prefix.rstrip("/") + "/"
    values = {raw.decode("utf-8", "surrogateescape").rstrip("/") for raw in listed.stdout.split(b"\0") if raw}
    return sorted(path[len(lead):] for path in values if path.startswith(lead))


def _snapshot(top: Path, run_dir: Path, prefix: str) -> str:
    with tempfile.TemporaryDirectory(prefix="shiploop-prepare-") as scratch:
        try:
            return lint.snapshot_tree(top, Path(run_dir), Path(scratch) / "index", prefix=prefix)
        except (OSError, lint.LintError) as exc:
            raise PreparationError("cannot snapshot the prepare-entry tree") from exc


def _unknown(identity: Mapping[str, str], action_id: str, *, reason: str,
             top: str = "", prefix: str = ".", lineage: Sequence[str] = ()) -> dict[str, Any]:
    return {"schema": SCHEMA, **identity, "status": "unknown", "reason": reason,
            "entry_action": action_id, "lineage": list(lineage) or [action_id],
            "toplevel": top, "prefix": prefix, "entry_head": "", "entry_tree": "", "dirty_paths": []}


def capture_entry(run_dir: Path, state: Mapping[str, Any], action_id: str, *, already_issued: bool = False
                  ) -> dict[str, Any]:
    """Record prepare entry once; a missing record after packet issue becomes an irreversible unknown marker."""
    identity = _identity(Path(run_dir), state)
    prior = _read_record(Path(run_dir))
    if prior is not None:
        if any(prior.get(key) != value for key, value in identity.items()):
            raise PreparationError("the preparation record belongs to another run or repository; ownership is unknown")
        if prior.get("status") == "ready":
            lineage = _lineage(state, action_id)
            if any(action not in lineage for action in prior.get("lineage", ())):
                raise PreparationError("the preparation action lineage changed; ownership is unknown")
            if list(prior.get("lineage", ())) != lineage:
                prior["lineage"] = lineage
                _write_record(Path(run_dir), prior)
            return prior
        return prior
    lineage = _lineage(state, action_id)
    if (already_issued or _packet_recorded(Path(run_dir), action_id)
            or any(row.get("stage") == "prepare" for row in state.get("history", ())
                   if isinstance(row, Mapping))):
        record = _unknown(
            identity, action_id,
            reason="the prepare packet was already issued but its entry snapshot is missing", lineage=lineage)
        _write_record(Path(run_dir), record)
        return record
    repo = Path(identity["repo"])
    top = lint.git_toplevel(repo)
    if top is None:
        record = _unknown(identity, action_id, reason="the prepare entry is not a Git checkout", lineage=lineage)
        _write_record(Path(run_dir), record)
        return record
    prefix = lint.scope_prefix(top, repo)
    head = lint._head(top)
    if not _OBJECT_ID.fullmatch(head):
        record = _unknown(identity, action_id, reason="the prepare entry has no committed Git HEAD", top=str(top),
                          prefix=prefix, lineage=lineage)
        _write_record(Path(run_dir), record)
        return record
    dirty = _dirty_paths(top, prefix)
    ignored = _ignored_paths(top, prefix)
    tree = _snapshot(top, Path(run_dir), prefix)
    head_tree = shiploop_git.git(top, "rev-parse", "--verify", "HEAD^{tree}")
    entry_tree = head_tree.stdout.strip()
    if head_tree.returncode or not _OBJECT_ID.fullmatch(entry_tree):
        record = _unknown(identity, action_id, reason="the prepare entry tree cannot be identified", top=str(top),
                          prefix=prefix, lineage=lineage)
        _write_record(Path(run_dir), record)
        return record
    record = {"schema": SCHEMA, **identity, "status": "ready", "reason": "",
              "entry_action": action_id, "lineage": lineage, "toplevel": str(top), "prefix": prefix,
              "entry_head": head, "head_tree": entry_tree, "entry_tree": tree, "dirty_paths": dirty,
              "ignored_paths": ignored,
              "pending": None}
    _write_record(Path(run_dir), record)
    return record


def _matches_identity(record: Mapping[str, Any], run_dir: Path, state: Mapping[str, Any]) -> bool:
    try:
        identity = _identity(run_dir, state)
    except PreparationError:
        return False
    return all(record.get(key) == value for key, value in identity.items())


def _current_tree(top: Path, run_dir: Path, prefix: str) -> str:
    return _snapshot(top, run_dir, prefix)


def _changed_paths(top: Path, prefix: str, before_tree: str, after_tree: str) -> list[str]:
    result = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--name-only", before_tree, after_tree)
    if result.returncode:
        raise PreparationError("cannot compare the prepare-entry and current trees")
    names = [raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw]
    lead = "" if prefix in ("", ".") else prefix.rstrip("/") + "/"
    return sorted(path[len(lead):] for path in names
                  if path.startswith(lead) and not lint._runtime_path(path))


def _knowledge_path(path: str) -> bool:
    return path == _KNOWLEDGE_HOME or path.startswith(_KNOWLEDGE_HOME + "/")


def _eligible(changed: Sequence[str], declared: Sequence[str], dirty: Sequence[str], ignored: Sequence[str],
              never: Callable[[str], bool] | None) -> tuple[list[str], list[str]]:
    declared_set = set(declared)
    dirty_set = set(dirty)
    ignored_roots = tuple(path.rstrip("/") for path in ignored)
    chosen: list[str] = []
    left: list[str] = []
    for path in changed:
        was_ignored = any(path == root or path.startswith(root + "/") for root in ignored_roots)
        allowed = (path in declared_set and path not in dirty_set and not was_ignored and not _knowledge_path(path)
                   and not lint._runtime_path(path) and not (never is not None and never(path)))
        (chosen if allowed else left).append(path)
    return chosen, left


def _head(top: Path) -> tuple[str, str, str]:
    result = shiploop_git.git(top, "rev-parse", "--verify", "-q", "HEAD")
    head = result.stdout.strip() if result.returncode == 0 else ""
    if not head:
        return "", "", ""
    parent = shiploop_git.git(top, "rev-parse", "--verify", "HEAD^")
    tree = shiploop_git.git(top, "rev-parse", "--verify", "HEAD^{tree}")
    return (head, parent.stdout.strip() if parent.returncode == 0 else "",
            tree.stdout.strip() if tree.returncode == 0 else "")


def _commit_pending(repo: Path, top: Path, pending: Mapping[str, Any]) -> str:
    """Commit the durable exact-path plan and verify Git landed the recorded parent/tree."""
    paths = list(pending["paths"])
    parent = str(pending["parent"])
    tree = str(pending["tree"])
    try:
        committed = shiploop_git.commit_paths(repo, paths, str(pending.get("message") or _MESSAGE),
                                              literal_paths=True)
    except shiploop_git.CommitError as exc:
        raise PreparationError(
            "Git refused the prepare commit; no stage was advanced. Fix the cause and retry the same callback: "
            + str(exc)) from exc
    if not committed.commit:
        raise PreparationError("the pending prepare paths no longer produce a commit; no stage was advanced")
    landed, landed_parent, landed_tree = _head(top)
    if landed != committed.commit or landed_parent != parent or landed_tree != tree:
        raise PreparationError(
            "Git landed a prepare commit different from its durable parent/tree; no stage was advanced. "
            "Keep the files and resolve HEAD before retrying the same callback")
    return landed


def _notice(record: Mapping[str, Any], *, committed: Sequence[str] = (), left: Sequence[str] = (),
            reason: str = "", note: str = "") -> None:
    if committed:
        print("ShipLoop prepare committed the declared, clean-at-entry paths: " + ", ".join(committed) + ".")
    if left:
        print("ShipLoop prepare left these changed paths outside its phase commit: " + ", ".join(left) + ".")
    if reason:
        print("ShipLoop prepare ownership is unknown or incomplete: " + reason
              + ". No preparation paths were committed.")
    if note:
        print("ShipLoop prepare: " + note + ".")
    print("Knowledge-home files remain under the existing separate knowledge close. A declared path delta is scoped "
          "authority, not proof of who made a concurrent same-path edit.")


def packet_entry(run_dir: Path, state: Mapping[str, Any], action_id: str, *, already_issued: bool) -> str:
    """Ensure the first prepare packet has one durable snapshot; return a user-facing boundary note when unknown."""
    try:
        record = capture_entry(run_dir, state, action_id, already_issued=already_issued)
    except PreparationError as exc:
        return str(exc)
    if record.get("status") != "ready":
        return str(record.get("reason") or "the prepare entry could not be captured")
    return ""


def commit_transition(run_dir: Path, before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    """Commit accepted prepare paths before transition hooks capture the first item base; return its commit ID."""
    rows = after.get("history", ())[len(before.get("history", ())):]
    accepted = next((row for row in rows if isinstance(row, Mapping) and row.get("stage") == "prepare"), None)
    if accepted is None or accepted.get("outcome") != "done":
        return ""
    action_id = str(accepted.get("action") or "")
    try:
        record = _read_record(Path(run_dir))
    except PendingPreparationError:
        raise
    except PreparationError as exc:
        _notice({}, reason=str(exc))
        return ""
    if record is None:
        _notice({}, reason="the prepare packet has no saved entry snapshot")
        return ""
    if not _matches_identity(record, Path(run_dir), before):
        _notice(record, reason="the run or repository binding does not match")
        return ""
    if record.get("status") != "ready":
        _notice(record, reason=str(record.get("reason") or "the entry snapshot is unavailable"))
        return ""
    lineage = list(record.get("lineage", ()))
    if action_id not in lineage:
        _notice(record, reason="the accepted action is outside the recorded prepare lineage")
        return ""
    repo = Path(str(record["repo"]))
    top = lint.git_toplevel(repo)
    if top is None or str(top) != record.get("toplevel") or lint.scope_prefix(top, repo) != record.get("prefix"):
        _notice(record, reason="the Git toplevel or repository prefix changed")
        return ""
    pending = record.get("pending")
    if pending is not None:
        accepted_result = after.get("accepted", {}).get(action_id)
        try:
            current_result_sha = _result_sha256(accepted_result)
        except PreparationError as exc:
            raise _pending_result_error(
                Path(run_dir), "the accepted callback cannot be matched to the pending result") from exc
        if current_result_sha != pending.get("result_sha256"):
            raise _pending_result_error(
                Path(run_dir), "the accepted callback differs from the pending preparation result")
        if pending.get("action") != action_id:
            raise PreparationError("the pending prepare commit belongs to another action")
        current_head, current_parent, current_head_tree = _head(top)
        pending_paths = list(pending.get("paths") or ())
        if pending.get("parent") != record.get("entry_head"):
            raise PreparationError("the pending prepare commit is not on the saved prepare-entry HEAD")
        planned = shiploop_git.planned_tree(repo, pending_paths, literal_paths=True)
        if not planned or planned != pending.get("tree"):
            raise PreparationError(
                "the pending prepare tree changed; keep the files and fix the checkout, then retry the same callback")
        parent = str(pending.get("parent") or "")
        if current_head == parent:
            pass
        elif current_parent == parent and current_head_tree == pending.get("tree"):
            _notice(record, committed=pending_paths)
            return current_head
        else:
            raise PreparationError(
                "HEAD moved outside the exact pending prepare commit; keep the files and resolve the commit before "
                "retrying")
        latest_head, latest_parent, latest_tree = _head(top)
        if latest_head == parent:
            pass
        elif latest_parent == parent and latest_tree == pending.get("tree"):
            _notice(record, committed=pending_paths)
            return latest_head
        else:
            raise PreparationError(
                "HEAD moved outside the exact pending prepare commit; keep the files and resolve the commit before "
                "retrying")
        landed = _commit_pending(repo, top, pending)
        _notice(record, committed=pending_paths)
        return landed

    current_head, _, _ = _head(top)
    declared = after.get("accepted", {}).get(action_id, {}).get("paths", [])
    try:
        declared = normalise_paths(declared)
    except PreparationError as exc:
        raise PreparationError("accepted prepare paths are invalid: " + str(exc)) from exc
    try:
        current_tree = _current_tree(top, Path(run_dir), str(record["prefix"]))
        changed = _changed_paths(top, str(record["prefix"]), str(record["entry_tree"]), current_tree)
        ignored_now = _ignored_paths(top, str(record["prefix"]))
    except PreparationError as exc:
        _notice(record, reason=str(exc))
        return ""
    try:
        never = item_scope.withheld(Path(run_dir), after)
    except item_scope.ItemScopeError as exc:
        raise PreparationError("cannot read workspace commit exclusions: " + str(exc)) from exc
    chosen, left = _eligible(changed, declared, list(record.get("dirty_paths", ())),
                             list(record.get("ignored_paths", ())), never)
    still_ignored: list[str] = []
    for path in chosen:
        # check-ignore parses pathspec magic as unsupported syntax; its pathname arguments are literal after --.
        checked = shiploop_git.git(repo, "check-ignore", "-q", "--", "./" + path)
        if checked.returncode == 0:
            still_ignored.append(path)
        elif checked.returncode != 1:
            raise PreparationError("cannot determine whether a declared prepare path is ignored")
    if still_ignored:
        chosen = [path for path in chosen if path not in set(still_ignored)]
        left = sorted(set(left) | set(still_ignored))
    left = sorted(set(left) | (set(ignored_now) - set(record.get("ignored_paths", ()))))
    if not chosen:
        if left:
            _notice(record, left=left)
        else:
            _notice(record, note="no declared, clean-at-entry preparation paths changed")
        return ""
    if current_head != record.get("entry_head"):
        raise PreparationError(
            "HEAD moved during prepare; no preparation commit was made. Keep the files and resolve HEAD, then retry "
            "the same callback")
    tree = shiploop_git.planned_tree(repo, chosen, literal_paths=True)
    if not tree:
        raise PreparationError("cannot calculate the exact prepare commit tree; no stage was advanced")
    accepted_result = after.get("accepted", {}).get(action_id)
    try:
        saved_result = dict(accepted_result) if isinstance(accepted_result, Mapping) else accepted_result
        result_sha256 = _result_sha256(saved_result)
    except PreparationError as exc:
        raise PreparationError("cannot persist the exact accepted prepare result; no stage was advanced") from exc
    summary = str(saved_result.get("summary") or "").strip()
    message = _MESSAGE + ("\n\n" + summary if summary else "") + "\n\nPaths: " + ", ".join(chosen)
    record["pending"] = {"action": action_id, "parent": current_head, "tree": tree,
                         "paths": chosen, "message": message, "result": saved_result,
                         "result_sha256": result_sha256}
    _write_record(Path(run_dir), record)
    if _head(top)[0] != current_head:
        raise PreparationError(
            "HEAD moved while recording the prepare commit; keep the files and retry the same callback")
    landed = _commit_pending(repo, top, record["pending"])
    _notice(record, committed=chosen, left=left)
    return landed


__all__ = ("PreparationError", "RECORD_FILE", "SCHEMA", "capture_entry", "commit_transition", "normalise_paths",
           "packet_entry", "record_path")
