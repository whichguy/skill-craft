"""Durable, script-verifiable evidence for ShipLoop inner-loop checks.

This module intentionally has no command-line entrypoint.  The ShipLoop
orchestrator owns its Markdown state and calls these small, stdlib-only helpers
to create or validate evidence before it advances an inner-loop iteration.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


class EvidenceError(ValueError):
    """Raised when check or primary-commit evidence is missing or untrustworthy."""


_METADATA_PREFIXES = (".git", ".shiploop", ".worktrees")
_SECTION_HEADERS = ("Review:", "Changes:", "Validation:", "Key learnings:")
_PLACEHOLDER_RE = re.compile(
    r"^(?:[-*]\s*)?(?:n/?a|none|tbd|unknown|not applicable|same as above)\.?$",
    re.IGNORECASE,
)
_SUBJECTIVE_PROOF_RE = re.compile(
    r"(?:\b(?:looks|seems|appears|feels)\s+"
    r"(?:good|great|fine|correct|complete|ready|safe|sound)\b|"
    r"\b(?:good|great|excellent|high)\s+quality\b|"
    r"\bquality\s+(?:is|was|looks|seems|appears|feels)\s+"
    r"(?:good|great|fine|high|sufficient|proven)\b|"
    r"\b(?:correctness|quality|coverage)\s+(?:is|was)\s+"
    r"(?:proven|verified)\b|"
    r"\b(?:i|we)\s+(?:believe|think|feel)\s+(?:this|it)\s+"
    r"(?:is|was)\s+(?:correct|good|ready|complete)\b)",
    re.IGNORECASE,
)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _as_repo_root(repo: Path | str | os.PathLike[str]) -> Path:
    """Return the Git top-level for ``repo``, or fail without a shell."""
    raw = Path(repo)
    root = Path(os.path.abspath(os.fspath(raw)))
    if not root.is_dir():
        raise EvidenceError(f"repository is not a directory: {root}")
    completed = subprocess.run(
        ["git", "-C", os.fspath(root), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise EvidenceError("repository must be inside a Git worktree")
    top = completed.stdout.decode("utf-8", "replace").strip()
    if not top:
        raise EvidenceError("Git did not return a worktree root")
    return Path(os.path.abspath(top))


def _git_bytes(
    repo: Path, argv: Sequence[str], *, allow_failure: bool = False
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", os.fspath(repo), *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        if detail:
            detail = f": {detail[:240]}"
        raise EvidenceError(f"Git command failed{detail}")
    return completed.stdout


def _require_action_id(action_id: str) -> str:
    if (
        not isinstance(action_id, str)
        or not action_id.strip()
        or _CONTROL_RE.search(action_id)
    ):
        raise EvidenceError("action_id must be a nonempty single-line string")
    return action_id


def _relative_exclusion(root: Path, raw: str | os.PathLike[str]) -> str | None:
    """Return a lexical repo-relative exclusion, never resolving symlinks."""
    if not isinstance(raw, (str, os.PathLike)):
        raise EvidenceError("excluded paths must be strings or path-like values")
    value = os.fspath(raw)
    if not value:
        raise EvidenceError("excluded paths must not be empty")
    candidate = Path(value)
    if candidate.is_absolute():
        absolute = Path(os.path.abspath(value))
        try:
            candidate = absolute.relative_to(root)
        except ValueError:
            return None
    normalized = os.path.normpath(os.fspath(candidate)).replace(os.sep, "/")
    if normalized in (".", ""):
        raise EvidenceError("an exclusion must not be the repository root")
    if normalized == ".." or normalized.startswith("../"):
        raise EvidenceError("an exclusion must stay inside the repository")
    return normalized.rstrip("/")


def _effective_excluded(
    root: Path,
    excluded: Sequence[str | os.PathLike[str]] | None,
    evidence_dir: Path | None = None,
) -> list[str]:
    values = list(_METADATA_PREFIXES)
    for item in excluded or ():
        relative = _relative_exclusion(root, item)
        if relative is not None:
            values.append(relative)
    if evidence_dir is not None:
        relative = _relative_exclusion(root, evidence_dir)
        if relative is not None:
            values.append(relative)
    return sorted(set(values))


def _is_excluded(relative: str, exclusions: Sequence[str]) -> bool:
    return any(
        relative == item or relative.startswith(item + "/") for item in exclusions
    )


def _indexed_modes(root: Path) -> dict[str, str]:
    """Read index modes, so a deleted tracked file still has mode evidence."""
    result: dict[str, str] = {}
    for item in _git_bytes(root, ["ls-files", "--stage", "-z"]).split(b"\0"):
        if not item:
            continue
        metadata, separator, raw_path = item.partition(b"\t")
        if not separator:
            raise EvidenceError("unexpected Git index entry")
        mode = metadata.split(b" ", 1)[0].decode("ascii", "strict")
        result[os.fsdecode(raw_path)] = mode
    return result


def _safe_worktree_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise EvidenceError("Git returned an unsafe repository-relative path")
    return root.joinpath(*path.parts)


def _regular_file_digest(path: Path) -> str:
    """Hash a regular file without following a symlink substituted at open time."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise EvidenceError(
            f"cannot read working file without following links: {path}"
        ) from exc
    try:
        descriptor_stat = os.fstat(fd)
        if not stat.S_ISREG(descriptor_stat.st_mode):
            raise EvidenceError(
                f"working path changed type while fingerprinting: {path}"
            )
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(fd)


def fingerprint(repo: Path, excluded: list[str] = []) -> str:
    """Hash tracked plus unignored working files without following symlink targets.

    ``.git``, ``.shiploop``, and ``.worktrees`` are always metadata exclusions.
    Extra exclusions are repository-relative paths (or absolute paths inside the
    repository).  Missing tracked files, executable bits, file types, and
    symlink target strings all contribute to the digest.
    """
    root = _as_repo_root(repo)
    exclusions = _effective_excluded(root, excluded)
    indexed_modes = _indexed_modes(root)
    listed = _git_bytes(
        root,
        [
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--deduplicate",
            "-z",
        ],
    )
    relative_paths = sorted(
        {os.fsdecode(raw) for raw in listed.split(b"\0") if raw},
        key=lambda value: value.encode("utf-8", "surrogateescape"),
    )

    digest = hashlib.sha256()
    digest.update(b"shiploop-evidence-fingerprint-v1\0")
    for relative in relative_paths:
        if _is_excluded(relative, exclusions):
            continue
        path = _safe_worktree_path(root, relative)
        digest.update(b"path\0")
        digest.update(os.fsencode(relative))
        digest.update(b"\0")
        try:
            status = os.lstat(os.fspath(path))
        except FileNotFoundError:
            digest.update(b"kind\0missing\0mode\0")
            digest.update(indexed_modes.get(relative, "missing").encode("ascii"))
            digest.update(b"\0")
            continue

        digest.update(b"mode\0")
        digest.update(format(status.st_mode, "o").encode("ascii"))
        digest.update(b"\0")
        if stat.S_ISLNK(status.st_mode):
            digest.update(b"kind\0symlink\0target\0")
            digest.update(os.fsencode(os.readlink(os.fspath(path))))
            digest.update(b"\0")
        elif stat.S_ISREG(status.st_mode):
            digest.update(b"kind\0file\0sha256\0")
            digest.update(_regular_file_digest(path).encode("ascii"))
            digest.update(b"\0")
        elif stat.S_ISDIR(status.st_mode):
            # Git never lists a normal directory, but preserve type evidence if
            # a raced or unusual index entry becomes one.
            digest.update(b"kind\0directory\0")
        else:
            digest.update(b"kind\0special\0")
    return digest.hexdigest()


def _normalise_manifest(
    manifest: Any, produces: Sequence[str] | None = None
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise EvidenceError("manifest must be an object")
    allowed_manifest_keys = {"checks", "lint_not_applicable"}
    unknown = set(manifest) - allowed_manifest_keys
    if unknown:
        raise EvidenceError(
            f"manifest has unsupported fields: {', '.join(sorted(map(str, unknown)))}"
        )
    checks = manifest.get("checks")
    if not isinstance(checks, list) or not checks:
        raise EvidenceError("manifest.checks must be a nonempty list")

    expected_produces: set[str] | None = None
    if produces is not None:
        if not isinstance(produces, Sequence) or isinstance(produces, (str, bytes)):
            raise EvidenceError("produces must be a list of exact output strings")
        if any(not isinstance(item, str) or not item for item in produces):
            raise EvidenceError("each produce must be a nonempty string")
        if len(set(produces)) != len(produces):
            raise EvidenceError("produces must not contain duplicates")
        expected_produces = set(produces)

    normal_checks: list[dict[str, Any]] = []
    check_ids: set[str] = set()
    test_acceptance: set[str] = set()
    lint_count = 0
    for index, raw_check in enumerate(checks, start=1):
        if not isinstance(raw_check, Mapping):
            raise EvidenceError(f"check {index} must be an object")
        required = {"id", "kind", "argv", "acceptance"}
        missing = required - set(raw_check)
        extra = set(raw_check) - required
        if missing or extra:
            details = []
            if missing:
                details.append("missing " + ", ".join(sorted(missing)))
            if extra:
                details.append("unsupported " + ", ".join(sorted(extra)))
            raise EvidenceError(f"check {index} has " + "; ".join(details))
        check_id = raw_check["id"]
        kind = raw_check["kind"]
        argv = raw_check["argv"]
        acceptance = raw_check["acceptance"]
        if (
            not isinstance(check_id, str)
            or not check_id.strip()
            or _CONTROL_RE.search(check_id)
        ):
            raise EvidenceError(
                f"check {index}.id must be a nonempty single-line string"
            )
        if check_id in check_ids:
            raise EvidenceError(f"manifest has duplicate check id: {check_id}")
        check_ids.add(check_id)
        if kind not in {"lint", "test"}:
            raise EvidenceError(f"check {check_id}.kind must be lint or test")
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(part, str) or not part for part in argv)
        ):
            raise EvidenceError(
                f"check {check_id}.argv must be a nonempty string argv list"
            )
        if not isinstance(acceptance, list) or any(
            not isinstance(item, str) or not item for item in acceptance
        ):
            raise EvidenceError(
                f"check {check_id}.acceptance must be a list of exact output strings"
            )
        if len(set(acceptance)) != len(acceptance):
            raise EvidenceError(
                f"check {check_id}.acceptance must not contain duplicates"
            )
        if expected_produces is not None and any(
            item not in expected_produces for item in acceptance
        ):
            raise EvidenceError(
                f"check {check_id}.acceptance must use exact produces strings"
            )
        normal_check = {
            "id": check_id,
            "kind": kind,
            "argv": list(argv),
            "acceptance": list(acceptance),
        }
        normal_checks.append(normal_check)
        if kind == "lint":
            lint_count += 1
        else:
            test_acceptance.update(acceptance)

    if not any(check["kind"] == "test" for check in normal_checks):
        raise EvidenceError("manifest requires at least one test check")
    reason = manifest.get("lint_not_applicable")
    if lint_count == 0:
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or _CONTROL_RE.search(reason)
        ):
            raise EvidenceError(
                "manifest requires a lint check or a noncode lint_not_applicable reason"
            )
    elif reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise EvidenceError(
            "lint_not_applicable must be a nonempty reason when present"
        )
    if expected_produces is not None:
        uncovered = expected_produces - test_acceptance
        if uncovered:
            raise EvidenceError(
                "test acceptance does not cover produces: "
                + ", ".join(sorted(uncovered))
            )

    normal: dict[str, Any] = {"checks": normal_checks}
    if reason is not None:
        normal["lint_not_applicable"] = reason
    return normal


def validate_manifest(manifest: Any, produces: list[str]) -> dict[str, Any]:
    """Validate that exact test acceptance checks cover every declared produce."""
    return _normalise_manifest(manifest, produces)


def _manifest_digest(manifest: Any) -> tuple[dict[str, Any], str]:
    normal = _normalise_manifest(manifest)
    encoded = json.dumps(
        normal, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return normal, hashlib.sha256(encoded).hexdigest()


def _safe_log_stem(index: int, check_id: str) -> str:
    stem = _SAFE_FILENAME_RE.sub("-", check_id).strip(".-") or "check"
    return f"{index:02d}-{stem}"


def _write_log(path: Path, content: bytes) -> None:
    """Write a private log without changing the process-wide umask."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    else:
        try:
            existing = os.lstat(os.fspath(path))
        except FileNotFoundError:
            existing = None
        if existing is not None and stat.S_ISLNK(existing.st_mode):
            raise EvidenceError(f"refusing to write log through symlink: {path}")
    try:
        descriptor = os.open(os.fspath(path), flags, 0o600)
    except OSError as exc:
        raise EvidenceError(f"cannot write private evidence log: {path}") from exc
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as log_file:
            descriptor = -1
            log_file.write(content)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _ensure_private_evidence_dir(path: Path) -> None:
    """Create a new leaf evidence directory at 0700 without altering umask."""
    created = False
    try:
        path.mkdir(parents=True, mode=0o700)
        created = True
    except FileExistsError:
        pass
    try:
        status = os.lstat(os.fspath(path))
    except FileNotFoundError as exc:
        raise EvidenceError(f"evidence directory disappeared: {path}") from exc
    if not stat.S_ISDIR(status.st_mode):
        raise EvidenceError(f"evidence_dir must be a real directory: {path}")
    if created:
        os.chmod(path, 0o700)


def _utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _terminate_timed_out_process(
    process: subprocess.Popen[bytes],
) -> tuple[bytes, bytes]:
    """Stop a timed-out command, including its POSIX process group when available."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            return process.communicate(timeout=0.2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return process.communicate()
    process.kill()
    return process.communicate()


def _run_argv(
    argv: list[str], cwd: Path, timeout: float
) -> tuple[str, int | None, bytes, bytes]:
    """Run a check without a shell and return status, exit code, stdout, stderr."""
    popen_kwargs: dict[str, Any] = {
        "cwd": os.fspath(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "posix":
        # A fresh session gives the timed-out command a private process group,
        # so a child it spawns cannot outlive the evidence command.
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(argv, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stdout, stderr = _terminate_timed_out_process(process)
        return "timeout", None, _bytes(stdout), _bytes(stderr)
    return (
        ("passed" if process.returncode == 0 else "failed"),
        process.returncode,
        _bytes(stdout),
        _bytes(stderr),
    )


def _bytes(value: object) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8", "replace")
    return str(value).encode("utf-8", "replace")


def run_checks(
    repo: Path,
    manifest: Any,
    evidence_dir: Path,
    action_id: str,
    timeout: float = 60,
    excluded: list[str] = [],
) -> dict[str, Any]:
    """Run declared check argv lists and return compact, JSON-safe evidence.

    Standard output and standard error are written to files under
    ``evidence_dir``.  They are deliberately not included in the returned
    evidence, avoiding a prompt or log-output flood.
    """
    action = _require_action_id(action_id)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
    ):
        raise EvidenceError("timeout must be a positive number of seconds")
    root = _as_repo_root(repo)
    normalized, digest = _manifest_digest(manifest)
    logs_root = Path(os.path.abspath(os.fspath(evidence_dir)))
    if logs_root == root:
        raise EvidenceError("evidence_dir must not be the repository root")
    _ensure_private_evidence_dir(logs_root)
    effective_excluded = _effective_excluded(root, excluded, logs_root)
    before = fingerprint(root, effective_excluded)
    rows: list[dict[str, Any]] = []
    content_changed = False

    for index, check in enumerate(normalized["checks"], start=1):
        stem = _safe_log_stem(index, check["id"])
        stdout_log = logs_root / f"{stem}.stdout.log"
        stderr_log = logs_root / f"{stem}.stderr.log"
        log_path = logs_root / f"{stem}.log"
        status = "error"
        exit_code: int | None = None
        stdout = b""
        stderr = b""
        started_at = _utc_timestamp()
        started_monotonic = time.monotonic()
        try:
            status, exit_code, stdout, stderr = _run_argv(
                list(check["argv"]), root, float(timeout)
            )
        except OSError as exc:
            status = "error"
            stderr = f"{type(exc).__name__}: {exc}\n".encode("utf-8", "replace")
        finished_at = _utc_timestamp()
        duration_ms = int(round((time.monotonic() - started_monotonic) * 1000))
        _write_log(stdout_log, stdout)
        _write_log(stderr_log, stderr)
        _write_log(
            log_path,
            b"--- stdout ---\n" + stdout + b"\n--- stderr ---\n" + stderr,
        )
        checkpoint = fingerprint(root, effective_excluded)
        if checkpoint != before:
            content_changed = True
        rows.append(
            {
                "id": check["id"],
                "kind": check["kind"],
                "argv": list(check["argv"]),
                "acceptance": list(check["acceptance"]),
                "exit": exit_code,
                "status": status,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "stdout_log": os.fspath(stdout_log),
                "stderr_log": os.fspath(stderr_log),
                "log_path": os.fspath(log_path),
                "log_paths": {
                    "stdout": os.fspath(stdout_log),
                    "stderr": os.fspath(stderr_log),
                },
            }
        )

    after = fingerprint(root, effective_excluded)
    content_changed = content_changed or before != after
    all_passed = not content_changed and all(
        row["status"] == "passed" and row["exit"] == 0 for row in rows
    )
    return {
        "version": 1,
        "action": action,
        "action_id": action,
        "repo": os.fspath(root),
        "evidence_dir": os.fspath(logs_root),
        "excluded": effective_excluded,
        "manifest_digest": digest,
        "before_fingerprint": before,
        "after_fingerprint": after,
        "before": before,
        "after": after,
        "content_changed": content_changed,
        "checks": rows,
        "all_passed": all_passed,
    }


def _require_log(path_value: object, label: str) -> None:
    if not isinstance(path_value, str) or not path_value:
        raise EvidenceError(f"check is missing {label}")
    path = Path(path_value)
    try:
        status = os.lstat(os.fspath(path))
    except FileNotFoundError as exc:
        raise EvidenceError(f"check {label} does not exist") from exc
    if not stat.S_ISREG(status.st_mode):
        raise EvidenceError(f"check {label} must be a regular file")


def validate_results(
    evidence: Any,
    repo: Path,
    manifest: Any,
    action_id: str,
    excluded: list[str] = [],
) -> dict[str, Any]:
    """Reject stale, failed, incomplete, or manifest-mismatched check evidence."""
    action = _require_action_id(action_id)
    if not isinstance(evidence, Mapping):
        raise EvidenceError("check evidence must be an object")
    root = _as_repo_root(repo)
    if evidence.get("action") != action or evidence.get("action_id") != action:
        raise EvidenceError("check evidence action does not match this iteration")
    if evidence.get("repo") != os.fspath(root):
        raise EvidenceError("check evidence belongs to a different repository")
    normalized, digest = _manifest_digest(manifest)
    if evidence.get("manifest_digest") != digest:
        raise EvidenceError("check evidence manifest digest is stale")
    before = evidence.get("before_fingerprint")
    after = evidence.get("after_fingerprint")
    if not isinstance(before, str) or not isinstance(after, str) or before != after:
        raise EvidenceError("check evidence has missing or changed source fingerprints")
    if evidence.get("before") != before or evidence.get("after") != after:
        raise EvidenceError(
            "check evidence fingerprint aliases are incomplete or mismatched"
        )
    if (
        evidence.get("content_changed") is not False
        or evidence.get("all_passed") is not True
    ):
        raise EvidenceError("check evidence did not pass without changing content")
    evidence_dir_value = evidence.get("evidence_dir")
    if not isinstance(evidence_dir_value, str) or not evidence_dir_value:
        raise EvidenceError("check evidence is missing its evidence directory")
    effective_excluded = _effective_excluded(root, excluded, Path(evidence_dir_value))
    if evidence.get("excluded") != effective_excluded:
        raise EvidenceError("check evidence exclusions do not match this validation")
    if fingerprint(root, effective_excluded) != after:
        raise EvidenceError("check evidence is stale for the current working tree")

    rows = evidence.get("checks")
    if not isinstance(rows, list) or len(rows) != len(normalized["checks"]):
        raise EvidenceError("check evidence has missing or extra result rows")
    for expected, row in zip(normalized["checks"], rows):
        if not isinstance(row, Mapping):
            raise EvidenceError("check evidence row must be an object")
        for key in ("id", "kind", "argv", "acceptance"):
            if row.get(key) != expected[key]:
                raise EvidenceError(
                    f"check evidence row does not match manifest: {expected['id']}"
                )
        if (
            row.get("status") != "passed"
            or type(row.get("exit")) is not int
            or row.get("exit") != 0
        ):
            raise EvidenceError(f"check evidence did not pass: {expected['id']}")
        started_at = row.get("started_at")
        finished_at = row.get("finished_at")
        duration_ms = row.get("duration_ms")
        if not isinstance(started_at, str) or not isinstance(finished_at, str):
            raise EvidenceError(
                f"check execution timestamps are missing: {expected['id']}"
            )
        try:
            started_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            finished_time = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EvidenceError(
                f"check execution timestamps are malformed: {expected['id']}"
            ) from exc
        if (
            started_time.tzinfo is None
            or finished_time.tzinfo is None
            or finished_time < started_time
        ):
            raise EvidenceError(
                f"check execution timestamps are inconsistent: {expected['id']}"
            )
        if (
            isinstance(duration_ms, bool)
            or not isinstance(duration_ms, int)
            or duration_ms < 0
        ):
            raise EvidenceError(
                f"check execution duration is missing or invalid: {expected['id']}"
            )
        _require_log(row.get("stdout_log"), "stdout_log")
        _require_log(row.get("stderr_log"), "stderr_log")
        _require_log(row.get("log_path"), "log_path")
        if row.get("log_paths") != {
            "stdout": row.get("stdout_log"),
            "stderr": row.get("stderr_log"),
        }:
            raise EvidenceError(
                f"check evidence log paths are incomplete: {expected['id']}"
            )
    return evidence  # type: ignore[return-value]


def history(repo: Path, limit: int = 7, skip: int = 0) -> list[dict[str, str]]:
    """Return newest-first complete commit bodies, with deterministic pagination."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise EvidenceError("history limit must be a nonnegative integer")
    if isinstance(skip, bool) or not isinstance(skip, int) or skip < 0:
        raise EvidenceError("history skip must be a nonnegative integer")
    root = _as_repo_root(repo)
    if limit == 0:
        return []
    head = _git_bytes(root, ["rev-parse", "--verify", "HEAD"], allow_failure=True)
    if not head.strip():
        return []
    raw = _git_bytes(
        root,
        ["log", f"--max-count={limit}", f"--skip={skip}", "--format=%H%x00%B%x00"],
    )
    parts = raw.split(b"\0")
    result: list[dict[str, str]] = []
    for index in range(0, len(parts) - 1, 2):
        sha = parts[index]
        # Git's pretty printer inserts one record-separator newline between
        # format records.  It belongs to neither SHA nor body.
        if index and sha.startswith(b"\n"):
            sha = sha[1:]
        body = parts[index + 1]
        if not sha:
            continue
        if not re.fullmatch(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha):
            raise EvidenceError("Git history returned an invalid object SHA")
        result.append(
            {
                "sha": sha.decode("ascii", "strict"),
                "body": body.decode("utf-8", "replace"),
            }
        )
    return result


def _commit_body(root: Path, sha: str) -> str:
    raw = _git_bytes(root, ["show", "-s", "--format=%B", sha])
    return raw.decode("utf-8", "replace")


def _is_commit(root: Path, sha: str) -> bool:
    if not isinstance(sha, str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha
    ):
        return False
    completed = subprocess.run(
        ["git", "-C", os.fspath(root), "rev-parse", "--verify", f"{sha}^{{commit}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0


def _validate_structured_body(body: str, action_id: str) -> None:
    lines = body.rstrip("\n").splitlines()
    trailer = f"ShipLoop-Iteration: {action_id}"
    if not lines or lines[-1] != trailer:
        raise EvidenceError(
            "primary commit must end with the exact ShipLoop iteration trailer"
        )
    trailer_lines = [line for line in lines if line.startswith("ShipLoop-Iteration:")]
    if trailer_lines != [trailer]:
        raise EvidenceError(
            "primary commit has a missing, reused, or wrong iteration trailer"
        )
    header_indexes: list[int] = []
    for header in _SECTION_HEADERS:
        indexes = [index for index, line in enumerate(lines) if line == header]
        if len(indexes) != 1:
            raise EvidenceError(
                f"primary commit requires one nonempty {header} section"
            )
        header_indexes.append(indexes[0])
    if header_indexes != sorted(header_indexes) or header_indexes[-1] >= len(lines) - 1:
        raise EvidenceError(
            "primary commit sections must precede the iteration trailer"
        )
    section_boundaries = header_indexes[1:] + [len(lines) - 1]
    for header, start, end in zip(_SECTION_HEADERS, header_indexes, section_boundaries):
        content = "\n".join(lines[start + 1 : end]).strip()
        if not content or _PLACEHOLDER_RE.fullmatch(content):
            raise EvidenceError(
                f"primary commit {header} section must contain concrete evidence"
            )
    if _SUBJECTIVE_PROOF_RE.search(body):
        raise EvidenceError(
            "primary commit must cite evidence, not a subjective quality claim"
        )


def validate_commit(
    repo: Path,
    sha: str,
    previous_sha: str,
    action_id: str,
) -> dict[str, Any]:
    """Validate that the actual new HEAD is this iteration's primary commit.

    Empty Git commits are intentionally valid when they record an audit-only
    iteration.  The body still has to contain concrete review, change,
    validation, and learning sections; a section-shaped claim is not proof.
    """
    action = _require_action_id(action_id)
    root = _as_repo_root(repo)
    if not _is_commit(root, sha):
        raise EvidenceError("primary commit sha must be a full existing commit SHA")
    if not _is_commit(root, previous_sha):
        raise EvidenceError("previous_sha must be a full existing commit SHA")
    head = _git_bytes(root, ["rev-parse", "HEAD"]).decode("ascii", "strict").strip()
    if sha != head:
        raise EvidenceError("primary commit must be the actual current HEAD")
    if sha == previous_sha:
        raise EvidenceError(
            "primary commit must be strictly newer than the previous commit"
        )
    ancestor = subprocess.run(
        [
            "git",
            "-C",
            os.fspath(root),
            "merge-base",
            "--is-ancestor",
            previous_sha,
            sha,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if ancestor.returncode != 0:
        raise EvidenceError("primary commit must descend from previous_sha")
    body = _commit_body(root, sha)
    _validate_structured_body(body, action)
    changed_paths = _git_bytes(
        root, ["diff-tree", "--no-commit-id", "--name-only", "-r", sha]
    )
    return {
        "sha": sha,
        "body": body,
        "previous_sha": previous_sha,
        "action": action,
        "empty": not bool(changed_paths.strip()),
    }
