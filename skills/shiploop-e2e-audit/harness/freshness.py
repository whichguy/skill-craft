#!/usr/bin/env python3
"""Fail-closed publication freshness checks for the ShipLoop evaluator.

The evaluator may launch one model process only after this module has shown
that the selected ShipLoop package is the current published package.  The
check reads immutable Git objects into temporary bare repositories; it never
updates an operator checkout, installs a package, or executes fetched files.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import Any, Mapping


SCHEMA = "shiploop-e2e-freshness/1"
_OBJECT_ID = re.compile(r"[0-9a-f]{40,64}\Z")
_CATALOG_COMMIT_ID = re.compile(r"[0-9a-f]{40}\Z")
_IGNORED_NAMES = frozenset({".git", "__pycache__"})
_REGULAR_MODES = frozenset({"100644", "100755"})
_CATALOG_PATH = ".claude-plugin/marketplace.json"


@dataclass(frozen=True)
class Authority:
    """A fixed remote and branch that the evaluator is willing to trust."""

    url: str
    ref: str


@dataclass(frozen=True)
class FreshnessTarget:
    """One fixed selected skill whose published package must be current."""

    name: str
    source_skill: str
    plugin_root: str
    plugin_skill: str


_SHIPLOOP = FreshnessTarget("shiploop", "skills/shiploop", "plugins/shiploop", "skills/shiploop")
_IMPROVE = FreshnessTarget("improve", "skills/improve", "plugins/improve", "skills/improve")
_FRESHNESS_TARGETS = (_SHIPLOOP, _IMPROVE)


# These are module constants rather than evaluator options.  A live evaluation
# cannot redirect its freshness authority or bypass a publication check.  Tests
# replace the constants with disposable local repositories.
SOURCE_AUTHORITY = Authority(
    "https://github.com/whichguy/skill-craft.git", "refs/heads/main",
)
CATALOG_AUTHORITY = Authority(
    "https://github.com/whichguy/skill-craft-market.git", "refs/heads/main",
)


class FreshnessProblem(Exception):
    """A safe, intentionally non-sensitive reason why freshness is unknown."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TreeEntry:
    path: str
    mode: str
    object_id: str
    sha256: str


@dataclass(frozen=True)
class Tree:
    root: str
    entries: Mapping[str, TreeEntry]
    blobs: Mapping[str, bytes]

    def subtree(self, relative: str) -> "Tree":
        prefix = relative.rstrip("/") + "/"
        selected = {
            path[len(prefix):]: TreeEntry(
                path=path[len(prefix):], mode=row.mode,
                object_id=row.object_id, sha256=row.sha256,
            )
            for path, row in self.entries.items()
            if path.startswith(prefix)
        }
        if not selected:
            raise FreshnessProblem("required-package-tree-is-missing")
        return Tree(relative.rstrip("/"), selected, self.blobs)

    def data(self, relative: str) -> bytes:
        row = self.entries.get(relative)
        if row is None:
            raise FreshnessProblem("required-package-file-is-missing")
        try:
            return self.blobs[row.object_id]
        except KeyError as exc:
            raise FreshnessProblem("required-package-blob-is-missing") from exc


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tree_digest(entries: Mapping[str, TreeEntry]) -> str:
    rows = [
        {"path": path, "mode": row.mode, "sha256": row.sha256}
        for path, row in sorted(entries.items())
    ]
    return _sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _tree_summary(tree: Tree) -> dict[str, Any]:
    return {
        "root": tree.root,
        "files": len(tree.entries),
        "aggregate_sha256": _tree_digest(tree.entries),
    }


def _empty_skill_receipt(target: FreshnessTarget) -> dict[str, Any]:
    return {
        "name": target.name,
        "source": {
            "authority": {"url": SOURCE_AUTHORITY.url, "ref": SOURCE_AUTHORITY.ref},
            "head": None,
            "skill": None,
            "plugin": None,
            "version": None,
        },
        "published": {
            "authority": {"url": CATALOG_AUTHORITY.url, "ref": CATALOG_AUTHORITY.ref},
            "head": None,
            "catalog": None,
            "pin": None,
            "plugin": None,
            "skill": None,
            "version": None,
        },
        "selected": {"root": None, "files": None, "aggregate_sha256": None, "version": None},
        "comparisons": {
            "source_to_generated": "not-run",
            "source_to_published": "not-run",
            "selected_to_published": "not-run",
        },
    }


def _empty_receipt() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ready": False,
        "status": "freshness-unverified",
        "reason": "freshness-check-did-not-complete",
        "checked_at": _now(),
        "model_calls": 0,
        "skills": {target.name: _empty_skill_receipt(target) for target in _FRESHNESS_TARGETS},
    }


def _environment(env: Mapping[str, str] | None) -> dict[str, str]:
    """Remove ambient Git checkout/config routing from a temporary probe."""
    source = os.environ if env is None else env
    result = {str(key): str(value) for key, value in source.items()}
    for key in tuple(result):
        if key.startswith("GIT_"):
            result.pop(key, None)
    result["GIT_TERMINAL_PROMPT"] = "0"
    result["GIT_CONFIG_NOSYSTEM"] = "1"
    result["GIT_CONFIG_GLOBAL"] = os.devnull
    return result


def _git(
    git: str,
    arguments: list[str],
    *,
    env: Mapping[str, str],
    input_data: bytes | None = None,
    operation: str,
) -> bytes:
    try:
        completed = subprocess.run(
            [git, *arguments],
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=dict(env),
            timeout=45,
        )
    except FileNotFoundError as exc:
        raise FreshnessProblem("git-is-unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise FreshnessProblem(f"{operation}-timed-out") from exc
    except OSError as exc:
        raise FreshnessProblem(f"{operation}-could-not-start") from exc
    if completed.returncode != 0:
        # Deliberately never expose stderr: an authenticated remote can include
        # URLs, account names, or server text in it.
        raise FreshnessProblem(f"{operation}-failed")
    return completed.stdout


def _remote_head(git: str, authority: Authority, env: Mapping[str, str]) -> str:
    output = _git(
        git,
        ["ls-remote", "--refs", authority.url, authority.ref],
        env=env,
        operation="remote-head-query",
    )
    rows = [row for row in output.splitlines() if row]
    if len(rows) != 1:
        raise FreshnessProblem("remote-head-is-ambiguous-or-missing")
    try:
        object_id, ref = rows[0].split(b"\t", 1)
    except ValueError as exc:
        raise FreshnessProblem("remote-head-has-an-invalid-format") from exc
    try:
        object_text = object_id.decode("ascii")
        ref_text = ref.decode("ascii")
    except UnicodeDecodeError as exc:
        raise FreshnessProblem("remote-head-has-an-invalid-format") from exc
    if ref_text != authority.ref or not _OBJECT_ID.fullmatch(object_text):
        raise FreshnessProblem("remote-head-has-an-invalid-format")
    return object_text


def _initialize_bare(git: str, directory: Path, env: Mapping[str, str]) -> None:
    _git(git, ["init", "--bare", "--quiet", str(directory)], env=env, operation="temporary-repository-init")


def _fetch_commit(
    git: str, bare: Path, authority: Authority, object_id: str, env: Mapping[str, str], label: str,
) -> None:
    if not _OBJECT_ID.fullmatch(object_id):
        raise FreshnessProblem("requested-commit-has-an-invalid-format")
    _git(
        git,
        [
            "--no-optional-locks", f"--git-dir={bare}", "fetch", "--no-tags", "--quiet", "--depth=1",
            authority.url, object_id,
        ],
        env=env,
        operation=f"{label}-fetch",
    )
    _git(
        git,
        ["--no-optional-locks", f"--git-dir={bare}", "cat-file", "-e", f"{object_id}^{{commit}}"],
        env=env,
        operation=f"{label}-commit-verify",
    )


def _ignored(path: str) -> bool:
    parts = path.split("/")
    return any(part in _IGNORED_NAMES for part in parts) or parts[-1].endswith(".pyc")


def _batch_blobs(git: str, bare: Path, object_ids: list[str], env: Mapping[str, str]) -> dict[str, bytes]:
    unique = list(dict.fromkeys(object_ids))
    if not unique:
        return {}
    output = _git(
        git,
        ["--no-optional-locks", f"--git-dir={bare}", "cat-file", "--batch"],
        env=env,
        input_data=b"".join(object_id.encode("ascii") + b"\n" for object_id in unique),
        operation="package-blob-read",
    )
    position = 0
    result: dict[str, bytes] = {}
    for requested in unique:
        newline = output.find(b"\n", position)
        if newline < 0:
            raise FreshnessProblem("package-blob-response-is-truncated")
        header = output[position:newline].split()
        position = newline + 1
        if len(header) != 3:
            raise FreshnessProblem("package-blob-response-is-invalid")
        try:
            returned = header[0].decode("ascii")
            kind = header[1].decode("ascii")
            size = int(header[2].decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise FreshnessProblem("package-blob-response-is-invalid") from exc
        if returned != requested or kind != "blob" or size < 0 or position + size >= len(output) + 1:
            raise FreshnessProblem("package-blob-response-is-invalid")
        data = output[position:position + size]
        position += size
        if position >= len(output) or output[position:position + 1] != b"\n":
            raise FreshnessProblem("package-blob-response-is-truncated")
        position += 1
        result[requested] = data
    if position != len(output):
        raise FreshnessProblem("package-blob-response-has-trailing-data")
    return result


def _git_tree(git: str, bare: Path, object_id: str, root: str, env: Mapping[str, str]) -> Tree:
    output = _git(
        git,
        ["--no-optional-locks", f"--git-dir={bare}", "ls-tree", "-r", "-z", object_id, "--", root],
        env=env,
        operation="package-tree-read",
    )
    prefix = root.rstrip("/") + "/"
    preliminary: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for raw in output.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, encoded_path = raw.split(b"\t", 1)
            mode, kind, blob_id = metadata.split(b" ")
            full_path = os.fsdecode(encoded_path)
            mode_text = mode.decode("ascii")
            kind_text = kind.decode("ascii")
            object_text = blob_id.decode("ascii")
        except (UnicodeDecodeError, ValueError) as exc:
            raise FreshnessProblem("package-tree-has-an-invalid-entry") from exc
        if not full_path.startswith(prefix):
            raise FreshnessProblem("package-tree-has-an-invalid-entry")
        relative = full_path[len(prefix):]
        if not relative or relative.startswith("/") or ".." in relative.split("/"):
            raise FreshnessProblem("package-tree-has-an-invalid-entry")
        if _ignored(relative):
            continue
        if kind_text != "blob" or mode_text not in _REGULAR_MODES:
            raise FreshnessProblem("package-tree-has-an-unsupported-entry")
        if not _OBJECT_ID.fullmatch(object_text) or relative in seen:
            raise FreshnessProblem("package-tree-has-an-invalid-entry")
        seen.add(relative)
        preliminary.append((relative, mode_text, object_text))
    if not preliminary:
        raise FreshnessProblem("required-package-tree-is-missing")
    blobs = _batch_blobs(git, bare, [entry[2] for entry in preliminary], env)
    entries = {
        relative: TreeEntry(relative, mode, blob_id, _sha256(blobs[blob_id]))
        for relative, mode, blob_id in preliminary
    }
    return Tree(root.rstrip("/"), entries, blobs)


def _json_object(data: bytes, code: str) -> Mapping[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshnessProblem(code) from exc
    if not isinstance(value, Mapping):
        raise FreshnessProblem(code)
    return value


def _skill_version(data: bytes, code: str) -> str:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise FreshnessProblem(code) from exc
    if not lines or lines[0].strip() != "---":
        raise FreshnessProblem(code)
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("version:"):
            value = line.split(":", 1)[1].strip().strip("\"'")
            if value:
                return value
            break
    raise FreshnessProblem(code)


def _plugin_metadata(tree: Tree, target: FreshnessTarget, code: str) -> tuple[str, str]:
    metadata = _json_object(tree.data(".claude-plugin/plugin.json"), code)
    name, version = metadata.get("name"), metadata.get("version")
    if name != target.name or not isinstance(version, str) or not version:
        raise FreshnessProblem(code)
    return name, version


def _catalog_pin(tree: Tree, source_authority: Authority, target: FreshnessTarget) -> tuple[str, str]:
    catalog = _json_object(tree.data("marketplace.json"), "catalog-is-invalid")
    plugins = catalog.get("plugins")
    if not isinstance(plugins, list):
        raise FreshnessProblem("catalog-is-invalid")
    rows = [row for row in plugins if isinstance(row, Mapping) and row.get("name") == target.name]
    if len(rows) != 1:
        raise FreshnessProblem(f"catalog-{target.name}-entry-is-missing-or-duplicate")
    row = rows[0]
    version, source = row.get("version"), row.get("source")
    if not isinstance(version, str) or not version or not isinstance(source, Mapping):
        raise FreshnessProblem(f"catalog-{target.name}-entry-is-invalid")
    if (
        source.get("source") != "git-subdir"
        or source.get("url") != source_authority.url
        or source.get("path") != target.plugin_root
    ):
        raise FreshnessProblem(f"catalog-{target.name}-entry-is-invalid")
    ref, pinned = source.get("ref"), source.get("sha")
    if ref is not None and (not isinstance(ref, str) or not ref):
        raise FreshnessProblem(f"catalog-{target.name}-entry-is-invalid")
    if not isinstance(pinned, str) or not _CATALOG_COMMIT_ID.fullmatch(pinned):
        raise FreshnessProblem(f"catalog-{target.name}-pin-is-invalid")
    return pinned, version


def _local_tree(package: Mapping[str, Any]) -> tuple[Tree, str]:
    root_value = package.get("resolved_root") or package.get("root")
    if not isinstance(root_value, str) or not root_value:
        raise FreshnessProblem("selected-package-manifest-is-invalid")
    try:
        root = Path(root_value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise FreshnessProblem("selected-package-root-is-unavailable") from exc
    if not root.is_dir():
        raise FreshnessProblem("selected-package-root-is-unavailable")
    entries: dict[str, TreeEntry] = {}
    blobs: dict[str, bytes] = {}

    def walk(directory: Path, prefix: str) -> None:
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise FreshnessProblem("selected-package-cannot-be-read") from exc
        for child in children:
            if child.name in _IGNORED_NAMES or child.name.endswith(".pyc"):
                continue
            relative = f"{prefix}/{child.name}" if prefix else child.name
            try:
                status = child.lstat()
            except OSError as exc:
                raise FreshnessProblem("selected-package-cannot-be-read") from exc
            if stat.S_ISLNK(status.st_mode):
                raise FreshnessProblem("selected-package-has-an-unsupported-entry")
            if stat.S_ISDIR(status.st_mode):
                walk(child, relative)
                continue
            if not stat.S_ISREG(status.st_mode):
                raise FreshnessProblem("selected-package-has-an-unsupported-entry")
            try:
                data = child.read_bytes()
            except OSError as exc:
                raise FreshnessProblem("selected-package-cannot-be-read") from exc
            mode = "100755" if status.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else "100644"
            object_id = _sha256(data)
            entries[relative] = TreeEntry(relative, mode, object_id, object_id)
            blobs[object_id] = data

    walk(root, "")
    if not entries:
        raise FreshnessProblem("selected-package-is-empty")
    manifest_files = package.get("files")
    if not isinstance(manifest_files, list):
        raise FreshnessProblem("selected-package-manifest-is-invalid")
    expected_hashes: dict[str, str] = {}
    for row in manifest_files:
        if not isinstance(row, Mapping):
            raise FreshnessProblem("selected-package-manifest-is-invalid")
        logical_path, digest, provenance = row.get("logical_path"), row.get("sha256"), row.get("provenance")
        if (
            not isinstance(logical_path, str)
            or not logical_path
            or logical_path.startswith("@reference/")
            or logical_path.startswith("/")
            or ".." in logical_path.split("/")
            or not isinstance(digest, str)
            or not _OBJECT_ID.fullmatch(digest)
            or provenance != "in-package"
            or logical_path in expected_hashes
        ):
            raise FreshnessProblem("selected-package-manifest-is-invalid")
        if _ignored(logical_path):
            continue
        expected_hashes[logical_path] = digest
    actual_hashes = {path: row.sha256 for path, row in entries.items()}
    if expected_hashes != actual_hashes:
        raise FreshnessProblem("selected-package-changed-after-manifest")
    return Tree("selected", entries, blobs), str(root)


def _same(left: Tree, right: Tree) -> bool:
    return {
        path: (row.mode, row.sha256) for path, row in left.entries.items()
    } == {
        path: (row.mode, row.sha256) for path, row in right.entries.items()
    }


def _fail(receipt: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    receipt.update({"ready": False, "status": status, "reason": reason})
    return receipt


def _target_reason(target: FreshnessTarget, reason: str) -> str:
    """Keep legacy ShipLoop codes while identifying an Improve failure."""
    if target.name == "shiploop" or f"-{target.name}-" in reason:
        return reason
    return f"{target.name}-{reason}"


def _inspect_target(
    target: FreshnessTarget,
    package: Mapping[str, Any],
    receipt: dict[str, Any],
    git: str,
    source_bare: Path,
    catalog_bare: Path,
    source_head: str,
    catalog_head: str,
    env: Mapping[str, str],
) -> tuple[str, str]:
    skill_receipt = receipt["skills"][target.name]
    selected, selected_root = _local_tree(package)
    selected_version = _skill_version(selected.data("SKILL.md"), "selected-package-version-is-invalid")
    skill_receipt["selected"] = {**_tree_summary(selected), "root": selected_root, "version": selected_version}

    source_skill = _git_tree(git, source_bare, source_head, target.source_skill, env)
    source_plugin = _git_tree(git, source_bare, source_head, target.plugin_root, env)
    source_generated = source_plugin.subtree(target.plugin_skill)
    source_name, source_plugin_version = _plugin_metadata(
        source_plugin, target, "source-plugin-metadata-is-invalid",
    )
    source_skill_version = _skill_version(source_skill.data("SKILL.md"), "source-skill-version-is-invalid")
    source_generated_version = _skill_version(
        source_generated.data("SKILL.md"), "source-generated-skill-version-is-invalid",
    )
    skill_receipt["source"].update({
        "skill": _tree_summary(source_skill),
        "plugin": _tree_summary(source_plugin),
        "version": source_skill_version,
    })

    catalog_tree = _git_tree(git, catalog_bare, catalog_head, _CATALOG_PATH.rsplit("/", 1)[0], env)
    pinned, catalog_version = _catalog_pin(catalog_tree, SOURCE_AUTHORITY, target)
    skill_receipt["published"]["catalog"] = {
        "path": _CATALOG_PATH,
        "version": catalog_version,
        "source_url": SOURCE_AUTHORITY.url,
        "source_path": target.plugin_root,
        "pin_sha": pinned,
    }

    _fetch_commit(git, source_bare, SOURCE_AUTHORITY, pinned, env, "published-pin")
    published_plugin = _git_tree(git, source_bare, pinned, target.plugin_root, env)
    published_skill = published_plugin.subtree(target.plugin_skill)
    published_name, published_plugin_version = _plugin_metadata(
        published_plugin, target, "published-plugin-metadata-is-invalid",
    )
    published_skill_version = _skill_version(
        published_skill.data("SKILL.md"), "published-skill-version-is-invalid",
    )
    skill_receipt["published"].update({
        "pin": {"sha": pinned},
        "plugin": _tree_summary(published_plugin),
        "skill": _tree_summary(published_skill),
        "version": published_skill_version,
    })

    if source_name != target.name or published_name != target.name:
        raise FreshnessProblem("plugin-name-is-invalid")
    if len({source_skill_version, source_generated_version, source_plugin_version}) != 1:
        return "unpublished-source", "source-package-version-is-inconsistent"
    if len({catalog_version, published_skill_version, published_plugin_version}) != 1:
        return "freshness-unverified", "catalog-version-does-not-match-published-package"

    if not _same(source_skill, source_generated):
        skill_receipt["comparisons"]["source_to_generated"] = "different"
        return "unpublished-source", "source-and-generated-package-differ"
    skill_receipt["comparisons"]["source_to_generated"] = "matched"

    if not _same(source_plugin, published_plugin):
        skill_receipt["comparisons"]["source_to_published"] = "different"
        return "unpublished-source", "source-plugin-is-not-published"
    skill_receipt["comparisons"]["source_to_published"] = "matched"

    if selected_version != published_skill_version:
        skill_receipt["comparisons"]["selected_to_published"] = "different"
        return "installed-stale", "selected-package-version-does-not-match-published-package"
    if not _same(selected, published_skill):
        skill_receipt["comparisons"]["selected_to_published"] = "different"
        return "installed-stale", "selected-package-does-not-match-published-package"
    skill_receipt["comparisons"]["selected_to_published"] = "matched"
    return "ready", "selected-package-matches-current-publication"


def inspect_freshness(packages: Mapping[str, Mapping[str, Any]], git: str,
                      env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return a receipt proving both selected packages are current or stop.

    This is intentionally a read-only, no-model preflight. Its fixed ShipLoop
    and Improve authorities cannot be redirected through evaluator options.
    """
    receipt = _empty_receipt()
    current_target: FreshnessTarget | None = None
    try:
        if not isinstance(packages, Mapping):
            raise FreshnessProblem("selected-packages-manifest-is-invalid")
        selected_packages = {
            target.name: packages[target.name]
            for target in _FRESHNESS_TARGETS
        }
        if not all(isinstance(package, Mapping) for package in selected_packages.values()):
            raise FreshnessProblem("selected-packages-manifest-is-invalid")

        command_env = _environment(env)
        source_head = _remote_head(git, SOURCE_AUTHORITY, command_env)
        catalog_head = _remote_head(git, CATALOG_AUTHORITY, command_env)
        for target in _FRESHNESS_TARGETS:
            receipt["skills"][target.name]["source"]["head"] = source_head
            receipt["skills"][target.name]["published"]["head"] = catalog_head

        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-freshness-") as temporary:
            root = Path(temporary)
            source_bare = root / "source.git"
            catalog_bare = root / "catalog.git"
            _initialize_bare(git, source_bare, command_env)
            _initialize_bare(git, catalog_bare, command_env)
            _fetch_commit(git, source_bare, SOURCE_AUTHORITY, source_head, command_env, "source-head")
            _fetch_commit(git, catalog_bare, CATALOG_AUTHORITY, catalog_head, command_env, "catalog-head")
            for target in _FRESHNESS_TARGETS:
                current_target = target
                status, reason = _inspect_target(
                    target, selected_packages[target.name], receipt, git, source_bare,
                    catalog_bare, source_head, catalog_head, command_env,
                )
                if status != "ready":
                    return _fail(receipt, status, _target_reason(target, reason))
        return _fail(receipt, "ready", "selected-skill-packages-match-current-publication") | {"ready": True}
    except FreshnessProblem as exc:
        reason = _target_reason(current_target, exc.code) if current_target is not None else exc.code
        return _fail(receipt, "freshness-unverified", reason)
    except (OSError, TypeError, ValueError, KeyError):
        # Keep accidental implementation/parser errors fail-closed as well,
        # without serializing a raw exception that could include local paths.
        reason = "freshness-check-failed"
        if current_target is not None:
            reason = _target_reason(current_target, reason)
        return _fail(receipt, "freshness-unverified", reason)
