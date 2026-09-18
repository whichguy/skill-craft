#!/usr/bin/env python3
"""Read-only evidence collection for the ShipLoop one-shot experiment.

The helpers deliberately do not import or invoke ShipLoop.  They hash the
selected inputs, inspect Git through read-only commands, and copy a bounded
allowlist of run artifacts into a caller-owned archive.  Their observations
are diagnostics, never proof that an agent completed product work.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping

from capture import _sanitize_text


_IGNORED_NAMES = frozenset({".git", "__pycache__"})
_REPOSITORY_RUNTIME_DIRECTORIES = frozenset({
    ".cache", ".mypy_cache", ".npm", ".pytest_cache", ".ruff_cache",
    ".shiploop", ".shiploop-runs", ".until-loop", "__pycache__", "node_modules",
})
_SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
_SENSITIVE_NAMES = frozenset({
    "access_token", "access_token.json", "credentials", "credentials.json",
    "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa", "password", "secret",
    "secret.json", "token", "token.json",
})
_FENCE_OPEN = re.compile(r"^```shiploop-state[ \t]*$")
_FENCE_CLOSE = re.compile(r"^```[ \t]*$")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
_MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
_MAX_SCAN_ENTRIES = 4096


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_sha256(value: Any) -> str:
    return _sha256(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode())


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolved_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{label} does not resolve safely: {path}") from exc
    if not resolved.is_dir():
        raise ValueError(f"{label} is not a directory: {path}")
    return resolved


def _sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered == ".env" or (lowered.startswith(".env.") and not lowered.endswith(".example")):
        return True
    if lowered in _SENSITIVE_NAMES or lowered == "authorized_keys":
        return True
    return lowered.endswith(_SENSITIVE_SUFFIXES)


def _ignored_name(name: str) -> bool:
    return name in _IGNORED_NAMES or name.endswith(".pyc")


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise ValueError(f"cannot read evidence file: {path}") from exc
    return digest.hexdigest(), size


def _credential_shaped(data: bytes) -> bool:
    """Reject a raw artifact when the shared stream sanitizer would alter it."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return _sanitize_text(text) != text


def _provenance(target: Path, root: Path, source: str) -> str:
    return "in-package" if _within(target, root) else source


def _local_markdown_targets(record: Mapping[str, Any]) -> Iterable[str]:
    if not str(record["logical_path"]).endswith(".md"):
        return ()
    try:
        text = Path(str(record["resolved_path"])).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read Markdown reference: {record['logical_path']}") from exc
    targets: list[str] = []
    for match in _MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip("<>")
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith("/") or ":" in target:
            continue
        targets.append(target)
    return targets


def package_manifest(root: Path) -> dict[str, Any]:
    """Hash a skill package and explicitly retain any local external dependency.

    ``files`` is sorted by logical path.  A symlink or Markdown link which
    resolves outside ``root`` is included only after its target bytes are
    hashed, with an explicit provenance label.  Broken links and cycles fail
    closed rather than silently producing an incomplete package identity.
    """
    package_root = _resolved_directory(Path(root), "package root")
    skill = package_root / "SKILL.md"
    if not skill.is_file():
        raise ValueError(f"package is missing SKILL.md: {package_root}")

    files: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    logical_paths: dict[str, str] = {}
    active_directories: set[Path] = set()

    def add_file(logical_path: str, target: Path, source: str) -> None:
        try:
            resolved = target.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"unsafe package file link: {logical_path}") from exc
        if not resolved.is_file():
            raise ValueError(f"unsupported package link target: {logical_path}")
        resolved_text = str(resolved)
        previous = logical_paths.get(logical_path)
        if previous is not None:
            if previous != resolved_text:
                raise ValueError(f"ambiguous package logical path: {logical_path}")
            return
        digest, size = _file_digest(resolved)
        logical_paths[logical_path] = resolved_text
        files.append(
            {
                "logical_path": logical_path,
                "resolved_path": resolved_text,
                "sha256": digest,
                "bytes": size,
                "provenance": _provenance(resolved, package_root, source),
                "sensitive": _sensitive_name(target.name),
            }
        )

    def walk(logical_directory: str, directory: Path, source: str) -> None:
        try:
            resolved_directory = directory.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"unsafe package directory link: {logical_directory}") from exc
        if not resolved_directory.is_dir():
            raise ValueError(f"package directory target is not a directory: {logical_directory}")
        if resolved_directory in active_directories:
            raise ValueError(f"unsafe package symlink cycle: {logical_directory}")
        active_directories.add(resolved_directory)
        try:
            entries = sorted(directory.iterdir(), key=lambda child: child.name)
        except OSError as exc:
            raise ValueError(f"cannot scan package directory: {logical_directory}") from exc
        try:
            for entry in entries:
                if _ignored_name(entry.name):
                    continue
                logical_path = f"{logical_directory}/{entry.name}" if logical_directory else entry.name
                if entry.is_symlink():
                    try:
                        target = entry.resolve(strict=True)
                    except (OSError, RuntimeError) as exc:
                        raise ValueError(f"unsafe package symlink: {logical_path}") from exc
                    link_source = _provenance(target, package_root, "outside-package-symlink")
                    if target.is_dir():
                        walk(logical_path, target, link_source)
                    elif target.is_file():
                        add_file(logical_path, target, link_source)
                    else:
                        raise ValueError(f"unsupported package symlink target: {logical_path}")
                elif entry.is_dir():
                    walk(logical_path, entry, source)
                elif entry.is_file():
                    add_file(logical_path, entry, source)
                else:
                    skipped.append({"logical_path": logical_path, "reason": "nonregular-file"})
        finally:
            active_directories.remove(resolved_directory)

    walk("", package_root, "in-package")
    seen_references: set[str] = set()
    cursor = 0
    while cursor < len(files):
        record = files[cursor]
        cursor += 1
        for relative_target in _local_markdown_targets(record):
            source_path = Path(str(record["resolved_path"])).parent
            try:
                target = (source_path / relative_target).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise ValueError(f"unresolved package reference: {record['logical_path']} -> {relative_target}") from exc
            if _within(target, package_root):
                continue
            target_key = str(target)
            if target_key in seen_references:
                continue
            seen_references.add(target_key)
            reference_id = _sha256(f"{record['logical_path']}\0{relative_target}".encode())[:16]
            logical_path = f"@reference/{reference_id}/{target.name}"
            if target.is_dir():
                walk(logical_path, target, "outside-package-reference")
            elif target.is_file():
                add_file(logical_path, target, "outside-package-reference")
            else:
                raise ValueError(f"unsupported package reference: {record['logical_path']} -> {relative_target}")

    files.sort(key=lambda row: row["logical_path"])
    skipped.sort(key=lambda row: (row["logical_path"], row["reason"]))
    file_hashes = {row["logical_path"]: row["sha256"] for row in files}
    return {
        "root": str(Path(root).absolute()),
        "resolved_root": str(package_root),
        "files": files,
        "file_hashes": file_hashes,
        "aggregate_sha256": _json_sha256(file_hashes),
        "skipped": skipped,
    }


def _git(repo: Path, git_bin: str, *arguments: str, allow_one: bool = False) -> bytes:
    try:
        completed = subprocess.run(
            [git_bin, "--no-optional-locks", "-C", str(repo), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ValueError(f"cannot execute git for {repo}") from exc
    if completed.returncode != 0 and not (allow_one and completed.returncode == 1):
        raise ValueError(f"git {arguments[0] if arguments else 'command'} failed for {repo}")
    return completed.stdout


def _decode_path(raw: bytes) -> str:
    return os.fsdecode(raw)


def _status_rows(raw: bytes) -> list[dict[str, str]]:
    fields = raw.split(b"\0")
    rows: list[dict[str, str]] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4 or field[2:3] != b" ":
            raise ValueError("unsupported git porcelain status")
        row = {"index": field[:1].decode("ascii"), "worktree": field[1:2].decode("ascii"), "path": _decode_path(field[3:])}
        if row["index"] in {"R", "C"}:
            if index >= len(fields) or not fields[index]:
                raise ValueError("truncated git rename status")
            row["original_path"] = _decode_path(fields[index])
            index += 1
        rows.append(row)
    rows.sort(key=lambda row: (row["path"], row.get("original_path", ""), row["index"], row["worktree"]))
    return rows


def _index_rows(raw: bytes) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in raw.split(b"\0"):
        if not field:
            continue
        try:
            metadata, path = field.split(b"\t", 1)
            mode, object_id, stage = metadata.split(b" ")
        except ValueError as exc:
            raise ValueError("unsupported git index entry") from exc
        rows.append({"path": _decode_path(path), "mode": mode.decode("ascii"), "object": object_id.decode("ascii"), "stage": stage.decode("ascii")})
    rows.sort(key=lambda row: (row["path"], row["stage"], row["mode"], row["object"]))
    return rows


def _working_file(path: Path) -> tuple[str | None, int | None, str, bool]:
    try:
        path.lstat()
    except FileNotFoundError:
        return None, None, "missing", False
    except OSError as exc:
        raise ValueError(f"cannot inspect repository path: {path}") from exc
    if os.path.islink(path):
        try:
            data = os.fsencode(os.readlink(path))
        except OSError as exc:
            raise ValueError(f"cannot read repository symlink: {path}") from exc
        return _sha256(data), len(data), "symlink", True
    if not os.path.isfile(path):
        raise ValueError(f"unsupported repository path type: {path}")
    digest, size = _file_digest(path)
    return digest, size, "file", True


def _repository_relative(raw: str) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"unsafe repository path: {raw}")
    return relative


def _repository_skip(repo: Path, relative: Path) -> tuple[str, str] | None:
    """Return the reported root for metadata and conventional runtime inputs."""
    parts: list[str] = []
    for part in relative.parts:
        parts.append(part)
        path = Path(*parts).as_posix()
        if part == ".git":
            return path, "git-metadata"
        candidate = repo / path
        if (part in _REPOSITORY_RUNTIME_DIRECTORIES
                and not candidate.is_symlink() and candidate.is_dir()):
            return path, "runtime-cache-directory"
    if relative.name.endswith(".pyc"):
        return relative.as_posix(), "runtime-cache-file"
    return None


def repo_snapshot(repo: Path, git_bin: str = "git") -> dict[str, Any]:
    """Return a read-only, hash-only snapshot of a nonempty Git checkout.

    Git failures are errors rather than partial snapshots.  File contents are
    hashed from the working tree (or symlink target text) but are not copied,
    which avoids retaining arbitrary repository content or credentials.
    """
    requested = _resolved_directory(Path(repo), "repository")
    top = Path(_git(requested, git_bin, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != requested:
        raise ValueError(f"repository path must be its Git top level: {requested}")
    head = _git(top, git_bin, "rev-parse", "--verify", "--quiet", "HEAD", allow_one=True).decode().strip() or None
    if head is not None and not re.fullmatch(r"[0-9a-f]{40,64}", head):
        raise ValueError("Git HEAD is not a stable object id")
    branch_result = subprocess.run([git_bin, "-C", str(top), "symbolic-ref", "--quiet", "--short", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if branch_result.returncode not in (0, 1):
        raise ValueError(f"git symbolic-ref failed for {top}")
    branch = branch_result.stdout.decode().strip() or None
    status = _status_rows(_git(top, git_bin, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    index = _index_rows(_git(top, git_bin, "ls-files", "--stage", "-z"))
    tracked = {_decode_path(row) for row in _git(top, git_bin, "ls-files", "-z").split(b"\0") if row}
    untracked = {_decode_path(row) for row in _git(top, git_bin, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if row}
    ignored = {_decode_path(row) for row in _git(top, git_bin, "ls-files", "--others", "--ignored", "--exclude-standard", "-z").split(b"\0") if row}
    paths = sorted(tracked | untracked | ignored)
    files: list[dict[str, Any]] = []
    skipped_by_key: dict[tuple[str, str], dict[str, str]] = {}

    def skip(path: str, reason: str) -> None:
        skipped_by_key.setdefault((path, reason), {"path": path, "reason": reason})

    skip(".git", "git-metadata")
    for raw_relative in paths:
        relative_path = _repository_relative(raw_relative)
        # Explicitly tracked inputs remain part of the product, including a
        # vendored dependency or source under a conventional cache directory.
        exclusion = None if raw_relative in tracked else _repository_skip(top, relative_path)
        if exclusion is not None:
            skip(*exclusion)
            continue
        relative = relative_path.as_posix()
        candidate = top / relative_path
        digest, size, kind, exists = _working_file(candidate)
        files.append({"path": relative, "sha256": digest, "bytes": size, "kind": kind, "exists": exists, "tracked": relative in tracked, "untracked": relative in untracked, "ignored": relative in ignored, "sensitive": _sensitive_name(candidate.name)})
    status_lines = [
        f"{row['index']}{row['worktree']} {row['path']}" + (f" <- {row['original_path']}" if "original_path" in row else "")
        for row in status
    ]
    index_lines = [f"{row['mode']} {row['object']} {row['stage']}\t{row['path']}" for row in index]
    return {
        "repo": str(Path(repo).absolute()),
        "resolved_repo": str(top),
        "head": head,
        "unborn": head is None,
        "branch": branch,
        "status": status,
        "status_lines": status_lines,
        "status_sha256": _sha256(("\n".join(status_lines) + "\n").encode()),
        "index": {"entries": index_lines, "sha256": _sha256(("\n".join(index_lines) + "\n").encode())},
        "files": files,
        "skipped": sorted(skipped_by_key.values(), key=lambda row: (row["path"], row["reason"])),
    }


def _file_map(snapshot: Mapping[str, Any]) -> dict[str, tuple[Any, Any, Any]]:
    rows = snapshot.get("files")
    if not isinstance(rows, list):
        raise ValueError("snapshot lacks files")
    result: dict[str, tuple[Any, Any, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise ValueError("snapshot has an invalid file row")
        result[row["path"]] = (row.get("sha256"), row.get("kind"), row.get("exists"))
    return result


def compare_repos(before: Mapping[str, Any], after: Mapping[str, Any], repo: Path, git_bin: str = "git") -> dict[str, Any]:
    """Describe repository continuity and churn without classifying a rewrite."""
    current = _resolved_directory(Path(repo), "repository")
    expected = str(current)
    if before.get("resolved_repo") != expected or after.get("resolved_repo") != expected:
        raise ValueError("snapshots do not identify the requested repository")
    old_head, new_head = before.get("head"), after.get("head")
    if old_head is not None and not isinstance(old_head, str):
        raise ValueError("snapshots lack Git HEAD identity")
    if new_head is not None and not isinstance(new_head, str):
        raise ValueError("snapshots lack Git HEAD identity")
    if old_head is not None and new_head is not None:
        try:
            ancestor = subprocess.run([git_bin, "-C", str(current), "merge-base", "--is-ancestor", old_head, new_head], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except OSError as exc:
            raise ValueError(f"cannot execute git for {current}") from exc
        if ancestor.returncode not in (0, 1):
            raise ValueError(f"git merge-base failed for {current}")
        old_head_is_ancestor: bool | None = ancestor.returncode == 0
        ancestry = "ancestor" if old_head_is_ancestor else "not-ancestor"
    else:
        old_head_is_ancestor = None
        ancestry = "not-applicable-no-baseline-head" if old_head is None else "not-comparable-current-head-missing"
    before_files, after_files = _file_map(before), _file_map(after)
    added = sorted(set(after_files) - set(before_files))
    removed = sorted(set(before_files) - set(after_files))
    changed = sorted(path for path in set(before_files) & set(after_files) if before_files[path] != after_files[path])
    return {
        "repository_identity_matches": True,
        "old_head": old_head,
        "new_head": new_head,
        "old_head_is_ancestor": old_head_is_ancestor,
        "ancestry": ancestry,
        "added_paths": added,
        "removed_paths": removed,
        "changed_paths": changed,
        "churn": {"added": len(added), "removed": len(removed), "changed": len(changed), "total": len(added) + len(removed) + len(changed)},
        "diagnostic_note": "Path churn is descriptive only and does not establish whether work was incremental or rewritten.",
    }


def _artifact_kind(relative: Path, *, root_is_shiploop: bool = False) -> str | None:
    name, parts = relative.name, relative.parts
    if name in {"state.md", "workspace.md", "return-plan.md", "return-receipt.md", "report.html"}:
        return name.rsplit(".", 1)[0]
    if len(parts) >= 2 and parts[-2] in {"results", "inbox"} and name.endswith(".md"):
        return "result" if parts[-2] == "results" else "inbox"
    if (root_is_shiploop or ".shiploop" in parts) and name in {"metadata.json", "manifest.json"}:
        return "shiploop-metadata"
    return None


def capture_run_artifacts(roots: list[Path], output: Path) -> dict[str, Any]:
    """Archive a bounded allowlist of run evidence under ``output``.

    Only symlinks resolving inside their supplied owned root are followed.  The
    result contains source absolute paths and digest-addressed archive paths so
    a caller can correlate a live run with its immutable copied evidence.
    """
    if not roots:
        raise ValueError("at least one artifact root is required")
    skipped: list[dict[str, str]] = []
    owned_roots: list[Path] = []
    for supplied in roots:
        candidate = Path(supplied)
        if not candidate.exists() and not candidate.is_symlink():
            skipped.append({"source_path": str(candidate.absolute()), "reason": "missing-root"})
            continue
        owned_roots.append(_resolved_directory(candidate, "artifact root"))
    archive_root = Path(output).resolve(strict=False)
    if any(_within(archive_root, root) for root in owned_roots):
        raise ValueError("artifact output must be outside each owned root")
    archive_root.mkdir(parents=True, exist_ok=True)
    blobs = archive_root / "blobs"
    artifacts: list[dict[str, Any]] = []
    scanned = 0

    def capture_file(root: Path, source: Path, relative: Path, kind: str) -> None:
        try:
            resolved = source.resolve(strict=True)
        except (OSError, RuntimeError):
            skipped.append({"source_path": str(source.absolute()), "reason": "unsafe-symlink"})
            return
        if not _within(resolved, root):
            skipped.append({"source_path": str(source.absolute()), "reason": "symlink-outside-owned-root"})
            return
        if not resolved.is_file():
            skipped.append({"source_path": str(source.absolute()), "reason": "nonregular-artifact"})
            return
        try:
            data = resolved.read_bytes()
        except OSError:
            skipped.append({"source_path": str(source.absolute()), "reason": "unreadable-artifact"})
            return
        digest = _sha256(data)
        if len(data) > _MAX_ARTIFACT_BYTES:
            skipped.append({"source_path": str(source.absolute()), "sha256": digest, "reason": "artifact-size-bound"})
            return
        if _credential_shaped(data):
            skipped.append({"source_path": str(source.absolute()), "sha256": digest, "reason": "credential-shaped-artifact"})
            return
        blob = blobs / digest
        if blob.exists() and _file_digest(blob)[0] != digest:
            raise ValueError(f"archive digest collision at {blob}")
        if not blob.exists():
            blobs.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(data)
        artifacts.append({"kind": kind, "root": str(root), "relative_path": relative.as_posix(), "source_path": str(source.absolute()), "resolved_path": str(resolved), "sha256": digest, "bytes": len(data), "archive_path": str(blob.relative_to(archive_root))})

    def walk(root: Path, current: Path, relative: Path, ancestry: set[Path]) -> None:
        nonlocal scanned
        try:
            resolved = current.resolve(strict=True)
        except (OSError, RuntimeError):
            skipped.append({"source_path": str(current.absolute()), "reason": "unsafe-symlink"})
            return
        if not _within(resolved, root):
            skipped.append({"source_path": str(current.absolute()), "reason": "symlink-outside-owned-root"})
            return
        if resolved in ancestry:
            skipped.append({"source_path": str(current.absolute()), "reason": "symlink-cycle"})
            return
        try:
            entries = sorted(current.iterdir(), key=lambda child: child.name)
        except OSError:
            skipped.append({"source_path": str(current.absolute()), "reason": "unreadable-directory"})
            return
        next_ancestry = ancestry | {resolved}
        for entry in entries:
            scanned += 1
            if scanned > _MAX_SCAN_ENTRIES:
                skipped.append({"source_path": str(root), "reason": "scan-entry-bound"})
                return
            if _ignored_name(entry.name):
                continue
            child_relative = relative / entry.name
            kind = _artifact_kind(child_relative, root_is_shiploop=root.name == ".shiploop")
            if entry.is_symlink():
                try:
                    target = entry.resolve(strict=True)
                except (OSError, RuntimeError):
                    skipped.append({"source_path": str(entry.absolute()), "reason": "unsafe-symlink"})
                    continue
                if not _within(target, root):
                    skipped.append({"source_path": str(entry.absolute()), "reason": "symlink-outside-owned-root"})
                elif target.is_dir():
                    walk(root, target, child_relative, next_ancestry)
                elif kind is not None:
                    capture_file(root, entry, child_relative, kind)
            elif entry.is_dir():
                walk(root, entry, child_relative, next_ancestry)
            elif kind is not None:
                capture_file(root, entry, child_relative, kind)

    for root in owned_roots:
        walk(root, root, Path(), set())
    artifacts.sort(key=lambda row: (row["source_path"], row["kind"]))
    skipped.sort(key=lambda row: (row["source_path"], row["reason"]))
    payload = {"schema": "shiploop-e2e-artifacts/v1", "output": str(archive_root), "roots": [str(root) for root in owned_roots], "artifacts": artifacts, "skipped": skipped}
    digest = _json_sha256(payload)
    manifest = archive_root / "manifests" / f"{digest}.json"
    if not manifest.exists():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**payload, "manifest_path": str(manifest.relative_to(archive_root)), "manifest_sha256": digest}


def _parse_shiploop_state(data: bytes) -> dict[str, Any]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("artifact is not UTF-8") from exc
    openings = [index for index, line in enumerate(lines) if _FENCE_OPEN.match(line)]
    if len(openings) != 1:
        raise ValueError("artifact must contain exactly one shiploop-state fence")
    closing = next((index for index in range(openings[0] + 1, len(lines)) if _FENCE_CLOSE.match(lines[index])), None)
    if closing is None:
        raise ValueError("artifact has an unterminated shiploop-state fence")

    def no_duplicates(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    try:
        state = json.loads("\n".join(lines[openings[0] + 1:closing]), object_pairs_hook=no_duplicates)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("artifact has invalid shiploop-state JSON") from exc
    if not isinstance(state, dict):
        raise ValueError("artifact state must be a JSON object")
    return state


def inspect_run_artifacts(capture: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect a result from :func:`capture_run_artifacts` without live reads.

    It reports only fields observed in archived Markdown state.  In particular,
    a navigator status or return receipt is not treated as semantic, deployed,
    or consumer-visible success.
    """
    output = _resolved_directory(Path(str(capture.get("output", ""))), "artifact archive")
    artifacts = capture.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("capture result lacks artifact rows")
    states: list[dict[str, Any]] = []
    workspaces: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ValueError("capture result has an invalid artifact row")
        archive_path = artifact.get("archive_path")
        if not isinstance(archive_path, str):
            raise ValueError("artifact has no archive path")
        archived = (output / archive_path).resolve(strict=True)
        if not _within(archived, output) or not archived.is_file():
            raise ValueError("artifact archive path escapes its output")
        data = archived.read_bytes()
        if artifact.get("sha256") != _sha256(data):
            raise ValueError("artifact archive digest does not match capture")
        base = {key: artifact.get(key) for key in ("source_path", "resolved_path", "sha256", "archive_path")}
        kind = artifact.get("kind")
        if kind in {"state", "workspace", "return-receipt"}:
            try:
                parsed = _parse_shiploop_state(data)
            except ValueError as exc:
                parsed = None
                parse_error = str(exc)
            else:
                parse_error = None
            if kind == "state":
                history = parsed.get("history") if isinstance(parsed, dict) else []
                transitions = [
                    {key: entry.get(key) for key in ("action", "stage", "outcome", "workitem")}
                    for entry in history if isinstance(entry, Mapping)
                ] if isinstance(history, list) else []
                states.append({**base, "state": parsed, "parse_error": parse_error, "status": parsed.get("status") if isinstance(parsed, dict) else None, "run_identity": {key: parsed.get(key) for key in ("run_id", "repo", "revision", "navigator_protocol_version")} if isinstance(parsed, dict) else None, "current_action": parsed.get("action") if isinstance(parsed, dict) else None, "action_transitions": transitions})
            elif kind == "workspace":
                workspaces.append({**base, "workspace": parsed, "parse_error": parse_error})
            else:
                receipts.append({**base, "receipt": parsed, "parse_error": parse_error})
    return {"states": states, "workspaces": workspaces, "guarded_receipt_presence": {"present": bool(receipts), "receipts": receipts}, "semantic_evidence": "not-assessed"}
