#!/usr/bin/env python3
"""Verify and refresh vendored plugin bundles under bundles/<plugin>/.

A vendored bundle is a byte-exact copy of committed upstream files. Its
bundle.json declares the member skills and agent cards; PROVENANCE.json
records the upstream commit and the sha256 and git blob id of every copied
file. install.sh never installs bundle members. scripts/sync-plugin-views.sh
generates plugins/<plugin>/ from the verified bundle.

Usage:
  sync-vendored-bundles.py --check [--bundle NAME] [--root DIR]
      Offline: reads only the filesystem (no git, no network). Verifies every
      bundle (or NAME) against its PROVENANCE.json and runs the publication
      lint. CI can prove that a bundle matches its own provenance record; it
      cannot prove equality with a private upstream. Only a local --from run
      can compare against upstream.

  sync-vendored-bundles.py --bundle NAME --from DIR [--ref REV] [--write]
      Refresh from an upstream git checkout outside skill-craft. Reads only
      committed blobs of REV (default refs/remotes/origin/main), so untracked,
      ignored or modified working-tree files never leak. REV must already be
      published on origin/main. An existing PROVENANCE.json must first match
      its own recorded upstream commit exactly (files, modes, blob ids and
      manifest); the release-policy checks then compare the old record with
      REV, even when bundle.json adds or drops a member. Without --write this
      is a dry run that prints the payload changes. With --write it stages the
      new tree outside the bundle, replaces the bundle's skills/ and agents/
      subtrees and PROVENANCE.json, then re-runs --check. It never edits
      bundle.json and never writes to DIR. Run scripts/sync-plugin-views.sh
      afterwards. The first import also needs --repository URL, an https URL
      without embedded credentials or a user name. The checkout's origin must
      be that one repository.

The publication lint covers the vendored files, bundle.json, PROVENANCE.json
and the upstream manifest description. It refuses absolute home paths (POSIX,
Windows and ~name/), email addresses outside reserved documentation domains,
common credential shapes (including JWTs, bearer tokens and credentials in a
URL), private, CGNAT and unique-local IP addresses, private host names in a
URL or host:port, hidden or bidirectional control characters, and (during
refresh) the operator's identity: the OS user name and the upstream git
user.name, or the comma-separated terms in SKILL_CRAFT_PUBLICATION_IDENTITY
when set. It is heuristic: a bare internal name such as printer.internal or
private context needs a human reading the diff.

Exit codes (a dry run exits 0 only when in sync; a lagging upstream can
also produce 2, 3 or 4, not just 1):
  0   ok (dry run: in sync, no payload change)
  1   verification failure, or a payload change found by a dry run that a
      --write refresh would apply (lag)
  2   upstream unavailable or invalid for this bundle (including a manifest
      description that no longer equals bundle.json)
  3   publication refusal (lint finding or a path skill-craft cannot publish)
  4   release-policy refusal (REV not published on origin/main, a payload
      change without an upstream manifest version increase, or a version
      that goes backwards)
  5   PROVENANCE.json does not match its recorded upstream commit (the
      record, not the upstream, is wrong)
  64  usage error
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlsplit

BUNDLE_FORMAT = "skill-craft-plugin-bundle/v1"
PROVENANCE_FORMAT = "skill-craft-vendored-bundle-provenance/v1"
BUNDLE_KEYS = frozenset({"format", "name", "description", "skills", "agents"})
DEFAULT_MANIFEST = ".claude-plugin/plugin.json"
PUBLISHED_REF = "refs/remotes/origin/main"
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
FILE_MODES = {"100644": False, "100755": True}
CONTROL_FILES = frozenset({"bundle.json", "PROVENANCE.json"})

# Local noise that is never part of a bundle (matches sync-plugin-views.sh).
NOISE_NAMES = frozenset({".DS_Store"})
NOISE_DIRS = frozenset({"__pycache__"})
NOISE_SUFFIXES = (".pyc",)

# One offline path rule for refresh and --check. These are the root
# .gitignore patterns plus the test tar-fixture excludes: a vendored path that
# matches one would silently disappear from a commit or a fixture copy.
UNPUBLISHABLE_PARTS = frozenset({
    ".claude", ".git", ".results", ".ruff_cache", ".shiploop", ".steer",
    "__pycache__", "dist", "node_modules", "results", "tasks",
})
UNPUBLISHABLE_NAMES = frozenset({".DS_Store"})
UNPUBLISHABLE_SUFFIXES = (".log", ".pyc")
UNPUBLISHABLE_GLOBS = ("REVIEW_CONVERGE.archived-*.md",)

# Required .gitattributes lines: vendored bytes (four upstream files depend on
# trailing spaces) and each generated bundle view must never be normalized.
BUNDLES_ATTRIBUTE = "bundles/** -text -whitespace"

# Publication lint. Reserved documentation names and placeholders are allowed
# so an ordinary refresh is not blocked by examples.
DOCUMENTATION_DOMAIN = re.compile(
    r"(?:^|\.)(?:example\.(?:com|net|org)|example|invalid|test|localhost)$", re.I
)
ALLOWED_EMAILS = frozenset({"git@github.com", "noreply@github.com"})
PLACEHOLDER_HOME_NAMES = frozenset({
    "default", "me", "public", "root", "runner", "shared", "user", "username", "you",
})
# The final label must be alphabetic so package pins such as name@1.2.3 are not
# mistaken for addresses.
EMAIL = re.compile(
    r"(?<![\w.+%-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![A-Za-z0-9-])"
)
HOME_PATH = re.compile(r"(?<![\w.~-])/(?:Users|home)/([A-Za-z0-9._-]+)")
# C:\Users\name and ~name/ are home paths too; placeholders stay allowed.
WINDOWS_HOME_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}([A-Za-z0-9._-]+)", re.I)
TILDE_HOME_PATH = re.compile(r"(?<![\w.~/-])~([A-Za-z][A-Za-z0-9._-]*)/")
# Private host names only in a host position (scheme://host or host:port), or
# with an unambiguous multi-label suffix. A bare name.local or this.internal is
# an ordinary code identifier (threading.local(), settings.local.json) and is
# left to the human review of the diff.
PRIVATE_HOST_SUFFIX = r"(?:local|lan|internal|intranet|corp|home\.arpa|ts\.net)"
# scheme://user:secret@host. A ${VAR}, $VAR, <placeholder> or %s secret, or a
# reserved documentation host, passes.
URL_CREDENTIALS = re.compile(
    r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s/@:]+:(?![$<{%])[^\s/@]+@([A-Za-z0-9.-]*[A-Za-z0-9])"
)
LINT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    # The lookbehind keeps words such as ask-agent-managed-worktree clean.
    ("API key", re.compile(r"(?<![A-Za-z0-9])sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    # A literal token needs a digit; placeholders such as <token> or $TOKEN pass.
    ("bearer token", re.compile(r"\bBearer[ \t]+(?=[A-Za-z0-9._~+/-]*\d)[A-Za-z0-9._~+/-]{20,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("private IPv4 address", re.compile(
        r"(?<![\d.])(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
        r"|192\.168(?:\.\d{1,3}){2}|169\.254(?:\.\d{1,3}){2})(?!\.?\d)"
    )),
    ("CGNAT IPv4 address", re.compile(
        r"(?<![\d.])100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2}(?!\.?\d)"
    )),
    ("unique-local IPv6 address", re.compile(
        r"(?<![0-9A-Za-z:])f[cd][0-9a-f]{2}(?::[0-9a-f]{0,4}){2,7}(?![0-9A-Za-z:])", re.I
    )),
    ("private host name", re.compile(
        r"(?:\b[A-Za-z][A-Za-z0-9+.-]*://(?:[^\s/@]*@)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\." + PRIVATE_HOST_SUFFIX
        + r"(?![A-Za-z0-9-]|\.[A-Za-z0-9])"
        r"|(?<![\w.-])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\." + PRIVATE_HOST_SUFFIX + r":\d{2,5}\b"
        r"|(?<![\w.-])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:home\.arpa|ts\.net)(?![A-Za-z0-9-]|\.[A-Za-z0-9]))",
        re.I,
    )),
    ("hidden or bidirectional control character",
     re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")),
)
IDENTITY_ENV = "SKILL_CRAFT_PUBLICATION_IDENTITY"
MIN_IDENTITY_TERM = 4


class Failure(Exception):
    """A classified refusal: code is the documented exit status."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_noise(relative: PurePosixPath) -> bool:
    return (
        relative.name in NOISE_NAMES
        or any(part in NOISE_DIRS for part in relative.parts)
        or relative.name.endswith(NOISE_SUFFIXES)
    )


def unpublishable_reason(path: str) -> str | None:
    """Return why skill-craft cannot publish this vendored path, if it cannot."""
    parts = PurePosixPath(path).parts
    for part in parts:
        if part in UNPUBLISHABLE_PARTS:
            return f"path component {part!r} is ignored or excluded by skill-craft"
    name = parts[-1] if parts else ""
    if name in UNPUBLISHABLE_NAMES or name.endswith(UNPUBLISHABLE_SUFFIXES):
        return f"file name {name!r} is ignored by skill-craft"
    for pattern in UNPUBLISHABLE_GLOBS:
        if fnmatch(name, pattern):
            return f"file name {name!r} matches ignored pattern {pattern}"
    return None


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def gitattributes_line(name: str) -> str:
    return f"plugins/{name}/** -text -whitespace"


def identity_terms(upstream: Path | None) -> list[str]:
    """Operator identity terms for the lint; the env override is exact."""
    if IDENTITY_ENV in os.environ:
        raw = [term.strip() for term in os.environ[IDENTITY_ENV].split(",")]
    elif upstream is None:
        return []
    else:
        raw = []
        try:
            raw.append(getpass.getuser())
        except (KeyError, OSError):
            pass
        result = subprocess.run(
            ["git", "-C", str(upstream), "config", "--get", "user.name"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            raw.append(result.stdout.strip())
    return sorted({term for term in raw if len(term) >= MIN_IDENTITY_TERM})


def lint_text(label: str, text: str, identity: Iterable[str] = ()) -> list[str]:
    """Return publication findings as 'label:line: rule' strings."""
    findings: list[str] = []
    identity_patterns = [
        (term, re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.I))
        for term in identity
    ]
    for number, line in enumerate(text.splitlines(), start=1):
        where = f"{label}:{number}"
        for pattern in (HOME_PATH, WINDOWS_HOME_PATH, TILDE_HOME_PATH):
            for match in pattern.finditer(line):
                if match.group(1).lower() not in PLACEHOLDER_HOME_NAMES:
                    findings.append(f"{where}: absolute home path")
        for match in EMAIL.finditer(line):
            address = f"{match.group(1)}@{match.group(2)}".lower()
            if address not in ALLOWED_EMAILS and not DOCUMENTATION_DOMAIN.search(match.group(2)):
                findings.append(f"{where}: email address")
        for match in URL_CREDENTIALS.finditer(line):
            if not DOCUMENTATION_DOMAIN.search(match.group(1)):
                findings.append(f"{where}: credentials in a URL")
        for rule, pattern in LINT_RULES:
            if pattern.search(line):
                findings.append(f"{where}: {rule}")
        for term, pattern in identity_patterns:
            if pattern.search(line):
                findings.append(f"{where}: operator identity term")
    return list(dict.fromkeys(findings))


def lint_bytes(label: str, data: bytes, identity: Iterable[str] = ()) -> list[str]:
    return lint_text(label, data.decode("utf-8", errors="replace"), identity)


def top_level_scalar(text: str, key: str) -> str | None:
    """Read one unindented frontmatter scalar from a SKILL.md."""
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return None
    body = text[4:text.index("\n---\n", 4)]
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.+?)[ \t]*$", body, re.M)
    return match.group(1).strip().strip("\"'") if match else None


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Failure(1, f"{label}: missing {path.name}") from None
    except (OSError, UnicodeError, ValueError) as exc:
        raise Failure(1, f"{label}: unreadable or invalid JSON {path.name}: {exc}") from None
    if not isinstance(value, dict):
        raise Failure(1, f"{label}: {path.name} must be a JSON object")
    return value


def name_list(value: Any, label: str, *, required: bool) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        raise Failure(1, f"{label} must be a {'non-empty ' if required else ''}list of names")
    if not all(isinstance(item, str) and NAME.fullmatch(item) for item in value):
        raise Failure(1, f"{label} entries must be normalized names")
    if len(set(value)) != len(value):
        raise Failure(1, f"{label} entries must be unique")
    return list(value)


def load_bundle(root: Path, name: str) -> dict[str, Any]:
    """Read and validate bundles/<name>/bundle.json."""
    label = f"bundles/{name}"
    data = load_json_object(root / "bundles" / name / "bundle.json", label)
    if set(data) != BUNDLE_KEYS:
        raise Failure(1, f"{label}/bundle.json keys must be exactly {sorted(BUNDLE_KEYS)}")
    if data["format"] != BUNDLE_FORMAT:
        raise Failure(1, f"{label}/bundle.json format must be {BUNDLE_FORMAT}")
    if data["name"] != name or not NAME.fullmatch(name):
        raise Failure(1, f"{label}/bundle.json name must equal its directory")
    if not isinstance(data["description"], str) or not data["description"].strip():
        raise Failure(1, f"{label}/bundle.json description must be a non-empty string")
    skills = name_list(data["skills"], f"{label}/bundle.json skills", required=True)
    name_list(data["agents"], f"{label}/bundle.json agents", required=False)
    if name not in skills:
        raise Failure(1, f"{label}/bundle.json skills must include the primary member {name}")
    return data


def include_roots(bundle: dict[str, Any]) -> list[str]:
    """Vendored roots are derived from bundle.json; nothing else is copied."""
    return [f"skills/{member}" for member in bundle["skills"]] + [
        f"agents/{agent}.md" for agent in bundle["agents"]
    ]


def within_roots(path: str, roots: Iterable[str]) -> bool:
    return any(
        path == root if root.endswith(".md") else path.startswith(root + "/")
        for root in roots
    )


def required_paths(bundle: dict[str, Any]) -> list[str]:
    return [f"skills/{member}/SKILL.md" for member in bundle["skills"]] + [
        f"agents/{agent}.md" for agent in bundle["agents"]
    ]


def bundle_names(root: Path) -> list[str]:
    directory = root / "bundles"
    if not directory.is_dir():
        return []
    return sorted(
        entry.name for entry in directory.iterdir()
        if entry.is_dir() and (entry / "bundle.json").is_file()
    )


def string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from string_values(item)


def repository_url_problem(url: Any) -> str | None:
    """Why a repository URL cannot be recorded publicly, if it cannot."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return "must be an https URL"
    try:
        parts = urlsplit(url)
    except ValueError:
        return "is not a valid URL"
    if "@" in parts.netloc or parts.username is not None or parts.password is not None:
        return "must not embed credentials or a user name"
    if not parts.hostname:
        return "has no host"
    return None


# A recorded path is either inside skills/<member>/ or is agents/<agent>.md.
RECORDED_PATH = re.compile(r"^(skills/[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)/.+$|^agents/[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.md$")


def validate_provenance_record(prov: dict[str, Any], name: str, label: str) -> list[dict[str, str]]:
    """Validate PROVENANCE.json on its own terms (schema, digests, paths).

    This does not consult bundle.json, so a refresh can compare an old record
    with a new upstream even after bundle.json adds or drops a member.
    """
    if set(prov) != {"format", "bundle", "upstream", "files"}:
        raise Failure(1, f"{label}/PROVENANCE.json keys must be format, bundle, upstream, files")
    if prov["format"] != PROVENANCE_FORMAT or prov["bundle"] != name:
        raise Failure(1, f"{label}/PROVENANCE.json format or bundle name is wrong")
    upstream = prov["upstream"]
    if not isinstance(upstream, dict) or set(upstream) != {"repository", "commit", "manifest"}:
        raise Failure(1, f"{label}/PROVENANCE.json upstream must hold exactly repository, commit, manifest")
    for url in (upstream["repository"],):
        problem = repository_url_problem(url)
        if problem == "must not embed credentials or a user name":
            raise Failure(3, f"{label}/PROVENANCE.json upstream repository URL {problem}")
        if problem:
            raise Failure(1, f"{label}/PROVENANCE.json upstream repositories must be https URLs ({problem})")
    if not isinstance(upstream["commit"], str) or not SHA1.fullmatch(upstream["commit"]):
        raise Failure(1, f"{label}/PROVENANCE.json upstream.commit must be a full 40-hex commit")
    manifest = upstream["manifest"]
    if not isinstance(manifest, dict) or set(manifest) != {"path", "name", "version", "sha256", "git_blob"}:
        raise Failure(1, f"{label}/PROVENANCE.json upstream.manifest has the wrong fields")
    if manifest["name"] != name or not isinstance(manifest["version"], str) \
            or not SEMVER.fullmatch(manifest["version"]):
        raise Failure(1, f"{label}/PROVENANCE.json manifest name/version is invalid")
    if not SHA256.fullmatch(str(manifest["sha256"])) or not SHA1.fullmatch(str(manifest["git_blob"])):
        raise Failure(1, f"{label}/PROVENANCE.json manifest digests are invalid")
    for value in string_values(prov):
        if value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value) or HOME_PATH.search(value):
            raise Failure(3, f"{label}/PROVENANCE.json contains an absolute local path")
    files = prov["files"]
    if not isinstance(files, list) or not files:
        raise Failure(1, f"{label}/PROVENANCE.json files must be a non-empty list")
    previous = ""
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "mode", "sha256", "git_blob"}:
            raise Failure(1, f"{label}/PROVENANCE.json file entries need path, mode, sha256, git_blob")
        path = entry["path"]
        pure = PurePosixPath(path) if isinstance(path, str) else None
        if pure is None or pure.is_absolute() or "\\" in path or any(
            part in ("", ".", "..") for part in path.split("/")
        ):
            raise Failure(1, f"{label}/PROVENANCE.json path is not confined: {path!r}")
        if path <= previous:
            raise Failure(1, f"{label}/PROVENANCE.json files must be sorted and unique: {path}")
        previous = path
        if not RECORDED_PATH.fullmatch(path):
            raise Failure(1, f"{label}/PROVENANCE.json path {path} is not under skills/<member>/ or agents/<agent>.md")
        if entry["mode"] not in FILE_MODES:
            raise Failure(1, f"{label}/PROVENANCE.json {path} mode must be 100644 or 100755")
        if not SHA256.fullmatch(str(entry["sha256"])) or not SHA1.fullmatch(str(entry["git_blob"])):
            raise Failure(1, f"{label}/PROVENANCE.json {path} digests are invalid")
    return files


def recorded_roots(files: list[dict[str, str]]) -> list[str]:
    """The member roots a validated record covers (skills/<m> or agents/<a>.md)."""
    roots = set()
    for entry in files:
        match = RECORDED_PATH.fullmatch(entry["path"])
        roots.add(match.group(1) if match and match.group(1) else entry["path"])
    return sorted(roots)


def validate_provenance(prov: dict[str, Any], bundle: dict[str, Any], label: str) -> list[dict[str, str]]:
    """Validate the record and that it covers exactly the declared members."""
    files = validate_provenance_record(prov, bundle["name"], label)
    roots = include_roots(bundle)
    for entry in files:
        if not within_roots(entry["path"], roots):
            raise Failure(1, f"{label}/PROVENANCE.json path {entry['path']} is outside the declared members")
    recorded = {entry["path"] for entry in files}
    for required in required_paths(bundle):
        if required not in recorded:
            raise Failure(1, f"{label}/PROVENANCE.json does not record declared {required}")
    return files


def check_bundle(root: Path, name: str, identity: Iterable[str] = ()) -> list[tuple[int, str]]:
    """Verify one bundle offline. Returns (exit class, message) problems."""
    label = f"bundles/{name}"
    directory = root / "bundles" / name
    problems: list[tuple[int, str]] = []
    try:
        bundle = load_bundle(root, name)
        prov = load_json_object(directory / "PROVENANCE.json", label)
        files = validate_provenance(prov, bundle, label)
    except Failure as exc:
        return [(exc.code, exc.message)]

    # The control files are published too: bundle.json's description reaches
    # every generated manifest, README and catalog, and PROVENANCE.json is
    # linked from the plugin README.
    for control in sorted(CONTROL_FILES):
        for finding in lint_bytes(f"{label}/{control}", (directory / control).read_bytes(), identity):
            problems.append((3, f"publication lint: {finding}"))

    recorded = {entry["path"]: entry for entry in files}
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        for entry_name in sorted(dirnames + filenames):
            full = Path(dirpath) / entry_name
            relative = PurePosixPath(full.relative_to(directory).as_posix())
            if full.is_symlink():
                problems.append((1, f"{label}: symlink is not allowed: {relative}"))
                continue
            if entry_name in dirnames or is_noise(relative):
                continue
            if str(relative) in CONTROL_FILES:
                continue
            if str(relative) not in recorded:
                problems.append((1, f"{label}: unrecorded file {relative}"))

    for path, entry in recorded.items():
        target = directory / path
        if target.is_symlink() or not target.is_file():
            problems.append((1, f"{label}: missing or non-regular vendored file {path}"))
            continue
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or git_blob_id(data) != entry["git_blob"]:
            problems.append((1, f"{label}: vendored bytes differ from PROVENANCE.json: {path}"))
        executable = bool(target.stat().st_mode & stat.S_IXUSR)
        if executable != FILE_MODES[entry["mode"]]:
            problems.append((1, f"{label}: executable bit differs from recorded mode {entry['mode']}: {path}"))
        reason = unpublishable_reason(path)
        if reason:
            problems.append((3, f"{label}: cannot publish {path}: {reason}"))
        for finding in lint_bytes(f"{label}/{path}", data, identity):
            problems.append((3, f"publication lint: {finding}"))

    primary = directory / "skills" / name / "SKILL.md"
    if primary.is_file():
        version = top_level_scalar(primary.read_text(encoding="utf-8", errors="replace"), "version")
        expected = prov["upstream"]["manifest"]["version"]
        if version != expected:
            problems.append((1, f"{label}: primary SKILL.md version {version!r} != upstream manifest version {expected!r}"))
    return problems


def check_gitattributes(root: Path, names: Iterable[str]) -> list[tuple[int, str]]:
    path = root / ".gitattributes"
    try:
        lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    except OSError:
        lines = set()
    problems = []
    for required in (BUNDLES_ATTRIBUTE, *(gitattributes_line(name) for name in names)):
        if required not in lines:
            problems.append((1, f".gitattributes must contain the line: {required}"))
    return problems


def run_check(root: Path, only: str | None) -> int:
    names = bundle_names(root)
    if only is not None:
        if only not in names:
            print(f"sync-vendored-bundles: no bundles/{only}/bundle.json", file=sys.stderr)
            return 1
        names = [only]
    identity = identity_terms(None)
    problems: list[tuple[int, str]] = []
    if names:
        problems.extend(check_gitattributes(root, names))
    for name in names:
        problems.extend(check_bundle(root, name, identity))
    for _, message in problems:
        print(f"sync-vendored-bundles: FAIL {message}", file=sys.stderr)
    if problems:
        return 3 if any(code == 3 for code, _ in problems) else 1
    print(f"sync-vendored-bundles: CHECK OK ({len(names)} bundle{'s' if len(names) != 1 else ''}; "
          "verified against PROVENANCE.json, not against upstream)")
    return 0


# --- refresh -----------------------------------------------------------------


def git(directory: Path, *args: str, binary: bool = False, code: int = 2) -> Any:
    result = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise Failure(code, f"git {' '.join(args)} failed: {detail or result.returncode}")
    return result.stdout if binary else result.stdout.decode("utf-8", errors="replace").strip()


def resolve_commit(top: Path, rev: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(top), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0 or not SHA1.fullmatch(result.stdout.strip()):
        raise Failure(2, f"upstream has no commit {rev} (fetch origin first)")
    return result.stdout.strip()


def normalize_repository(url: str) -> str:
    """Normalize https/ssh GitHub-style URLs so equivalent remotes compare equal."""
    value = url.strip()
    scp = re.fullmatch(r"[^@/\s]+@([^:/\s]+):(.+)", value)
    if scp:
        value = f"https://{scp.group(1)}/{scp.group(2)}"
    value = re.sub(r"^(?:ssh|git|https?)://", "https://", value)
    value = re.sub(r"^https://[^@/]+@", "https://", value)
    value = value.rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.casefold()


def semver_core(version: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(version)
    if not match:
        raise Failure(2, f"version is not semantic: {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def upstream_checkout(root: Path, source: Path) -> Path:
    if not source.is_dir():
        raise Failure(2, f"--from is not a directory: {source}")
    top = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    real_root = root.resolve()
    if top == real_root or real_root in top.parents or top in real_root.parents:
        raise Failure(2, "--from must be a git checkout outside skill-craft")
    return top


def list_upstream(top: Path, commit: str, roots: list[str]) -> list[tuple[str, str, str]]:
    """Return (path, mode, blob) for committed files under the roots."""
    raw = git(top, "ls-tree", "-r", "-z", "--full-tree", commit, "--", *roots, binary=True)
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, _, path_bytes = record.partition(b"\t")
        mode, kind, blob = meta.decode().split()
        path = path_bytes.decode("utf-8")
        if not within_roots(path, roots):
            continue
        if kind == "commit" or mode == "160000":
            raise Failure(2, f"upstream submodule is not allowed: {path}")
        if mode == "120000":
            raise Failure(2, f"upstream symlink is not allowed: {path}")
        if mode not in FILE_MODES or kind != "blob":
            raise Failure(2, f"upstream entry is not a regular file: {path} ({mode})")
        entries.append((path, mode, blob))
    return sorted(entries)


def verify_recorded_commit(top: Path, old: dict[str, Any], label: str) -> None:
    """Require the old PROVENANCE.json to describe its recorded commit exactly.

    CI can only check the bundle against its own record. Here, with upstream
    access, the record itself is checked: the file set, modes, blob ids and
    sha256 under the recorded member roots, and the manifest blob, must equal
    the recorded commit's tree. A mismatch means the record is false (exit 5),
    not that upstream moved.
    """
    upstream = old["upstream"]
    commit = upstream["commit"]
    present = subprocess.run(
        ["git", "-C", str(top), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True, check=False,
    )
    if present.returncode != 0:
        raise Failure(2, f"recorded upstream commit {commit} is not in the upstream checkout; fetch it first")
    files = old["files"]
    mismatched: set[str] = set()
    try:
        listed = list_upstream(top, commit, recorded_roots(files))
    except Failure as exc:
        raise Failure(5, f"{label}/PROVENANCE.json does not match its recorded upstream commit "
                         f"{commit[:12]}: {exc.message}") from None
    actual = {path: (mode, blob) for path, mode, blob in listed}
    recorded = {entry["path"]: entry for entry in files}
    mismatched.update(set(actual) ^ set(recorded))
    for path in set(actual) & set(recorded):
        mode, blob = actual[path]
        entry = recorded[path]
        if (mode, blob) != (entry["mode"], entry["git_blob"]):
            mismatched.add(path)
        elif hashlib.sha256(git(top, "cat-file", "blob", blob, binary=True)).hexdigest() != entry["sha256"]:
            mismatched.add(path)
    manifest = upstream["manifest"]
    manifest_listing = git(top, "ls-tree", "-z", "--full-tree", commit, "--", manifest["path"], binary=True)
    manifest_entries = [entry for entry in manifest_listing.split(b"\0") if entry]
    manifest_meta = manifest_entries[0].split(b"\t")[0].split() if len(manifest_entries) == 1 else []
    if len(manifest_meta) != 3 or manifest_meta[1] != b"blob" or manifest_meta[2].decode() != manifest["git_blob"] \
            or hashlib.sha256(git(top, "cat-file", "blob", manifest["git_blob"], binary=True)).hexdigest() \
            != manifest["sha256"]:
        mismatched.add(f"{manifest['path']} (manifest)")
    if mismatched:
        raise Failure(5, f"{label}/PROVENANCE.json does not match its recorded upstream commit {commit[:12]} "
                         "(the record is wrong, not upstream; restore it from version control):\n  "
                         + "\n  ".join(sorted(mismatched)))


def refresh(args: argparse.Namespace, root: Path) -> int:
    name = args.bundle
    label = f"bundles/{name}"
    bundle = load_bundle(root, name)
    directory = root / "bundles" / name
    old_path = directory / "PROVENANCE.json"
    old = load_json_object(old_path, label) if old_path.exists() else None
    if old is not None:
        # The old record is validated on its own terms, never against the
        # current bundle.json, so a membership change still meets the
        # release-policy checks below instead of needing a first import.
        validate_provenance_record(old, name, label)
        if args.repository:
            raise Failure(64, "--repository is only for the first import")
        repository = old["upstream"]["repository"]
        manifest_path = old["upstream"]["manifest"]["path"]
    else:
        if not args.repository:
            raise Failure(64, f"first import of {label} needs --repository URL")
        repository = args.repository
        manifest_path = DEFAULT_MANIFEST
        problem = repository_url_problem(repository)
        if problem:
            # Never echo the value: it may carry a token.
            raise Failure(64, f"--repository {problem}")

    top = upstream_checkout(root, Path(args.source))
    origin = git(top, "remote", "get-url", "origin")
    if normalize_repository(origin) != normalize_repository(repository):
        raise Failure(2, f"upstream origin does not match {label} provenance repository")
    if old is not None:
        verify_recorded_commit(top, old, label)
    published = resolve_commit(top, PUBLISHED_REF)
    commit = resolve_commit(top, args.ref or PUBLISHED_REF)
    ancestor = subprocess.run(
        ["git", "-C", str(top), "merge-base", "--is-ancestor", commit, published],
        capture_output=True, check=False,
    )
    if ancestor.returncode != 0:
        raise Failure(4, f"{commit} is not published on origin/main; push it upstream before vendoring")

    manifest_entries = [
        entry for entry in git(top, "ls-tree", "-z", "--full-tree", commit, "--", manifest_path,
                               binary=True).split(b"\0") if entry
    ]
    if len(manifest_entries) != 1 or not manifest_entries[0].split(b"\t")[0].startswith((b"100644 blob", b"100755 blob")):
        raise Failure(2, f"upstream {manifest_path} is missing or not a regular file")
    manifest_blob = manifest_entries[0].split(b"\t")[0].split()[2].decode()
    manifest_bytes = git(top, "cat-file", "blob", manifest_blob, binary=True)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Failure(2, f"upstream {manifest_path} is not valid JSON: {exc}") from None
    if not isinstance(manifest, dict) or manifest.get("name") != name:
        raise Failure(2, f"upstream {manifest_path} name must be {name}")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise Failure(2, f"upstream {manifest_path} version is not semantic")
    identity = identity_terms(top)
    # The description is published verbatim (bundle.json must equal it).
    description = manifest.get("description")
    if isinstance(description, str):
        described = lint_text(f"{manifest_path} description", description, identity)
        if described:
            raise Failure(3, "publication lint refused the upstream description:\n  " + "\n  ".join(described))
    if description != bundle["description"]:
        raise Failure(2, f"upstream {manifest_path} description differs from {label}/bundle.json; "
                         "review it and edit bundle.json deliberately")

    roots = include_roots(bundle)
    entries = list_upstream(top, commit, roots)
    paths = {path for path, _, _ in entries}
    for required in required_paths(bundle):
        if required not in paths:
            raise Failure(2, f"upstream {commit[:12]} has no declared {required}")
    refusals = [f"{path}: {reason}" for path in sorted(paths) if (reason := unpublishable_reason(path))]
    if refusals:
        raise Failure(3, "cannot publish upstream paths:\n  " + "\n  ".join(refusals))

    contents: dict[str, bytes] = {}
    findings: list[str] = []
    for path, _, blob in entries:
        data = git(top, "cat-file", "blob", blob, binary=True)
        if git_blob_id(data) != blob:
            raise Failure(2, f"upstream blob id mismatch for {path}")
        contents[path] = data
        findings.extend(lint_bytes(path, data, identity))
    if findings:
        raise Failure(3, "publication lint refused upstream content:\n  " + "\n  ".join(findings))

    primary_version = top_level_scalar(contents[f"skills/{name}/SKILL.md"].decode("utf-8", errors="replace"), "version")
    if primary_version != version:
        raise Failure(2, f"upstream primary SKILL.md version {primary_version!r} != {manifest_path} version {version!r}")

    upstream_record: dict[str, Any] = {"repository": repository}
    upstream_record.update(commit=commit, manifest={
        "path": manifest_path,
        "name": name,
        "version": version,
        "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "git_blob": manifest_blob,
    })
    provenance = {
        "format": PROVENANCE_FORMAT,
        "bundle": name,
        "upstream": upstream_record,
        "files": [
            {"path": path, "mode": mode, "sha256": hashlib.sha256(contents[path]).hexdigest(), "git_blob": blob}
            for path, mode, blob in entries
        ],
    }

    new_files = {entry["path"]: (entry["mode"], entry["sha256"]) for entry in provenance["files"]}
    old_files = {entry["path"]: (entry["mode"], entry["sha256"]) for entry in old["files"]} if old else {}
    added = sorted(set(new_files) - set(old_files))
    removed = sorted(set(old_files) - set(new_files))
    changed = sorted(path for path in set(new_files) & set(old_files) if new_files[path] != old_files[path])
    old_version = old["upstream"]["manifest"]["version"] if old else None
    old_commit = old["upstream"]["commit"] if old else None
    payload_changed = old is None or bool(added or removed or changed) or old_version != version

    print(f"{label}: upstream commit {old_commit or '(none)'} -> {commit}")
    print(f"{label}: upstream version {old_version or '(none)'} -> {version}")
    for heading, items in (("added", added), ("removed", removed), ("changed", changed)):
        for path in items:
            print(f"  {heading}: {path}")

    # Release policy applies whenever an old record exists, including a
    # membership change (bundle.json added or dropped a member).
    if old is not None and (added or removed or changed):
        if version == old_version:
            raise Failure(4, f"vendored bytes change but upstream version stays {version}; "
                             "release a new upstream version first (host caches need the update signal)")
    if old is not None and semver_core(version) < semver_core(old_version):
        raise Failure(4, f"upstream version {version} is lower than vendored {old_version}")

    if not payload_changed:
        print(f"{label}: payload unchanged" + ("" if commit == old_commit else " (provenance commit would advance)"))

    if not args.write:
        return 1 if payload_changed else 0

    with tempfile.TemporaryDirectory(prefix="skill-craft-vendor-") as temporary:
        staged = Path(temporary)
        for path, mode, _ in entries:
            target = staged / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents[path])
            target.chmod(0o755 if FILE_MODES[mode] else 0o644)
        for subtree in ("skills", "agents"):
            current = directory / subtree
            if current.is_symlink() or current.is_file():
                current.unlink()
            elif current.exists():
                shutil.rmtree(current)
            if (staged / subtree).exists():
                shutil.copytree(staged / subtree, current, symlinks=True)
    old_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{label}: wrote {len(entries)} vendored files and PROVENANCE.json")
    return run_check(root, name)


class UsageParser(argparse.ArgumentParser):
    def error(self, message: str):  # type: ignore[override]
        raise Failure(64, message)


def parse(argv: list[str] | None) -> argparse.Namespace:
    parser = UsageParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="offline verification")
    parser.add_argument("--bundle", help="bundle name (bundles/<name>)")
    parser.add_argument("--from", dest="source", help="upstream git checkout to refresh from")
    parser.add_argument("--ref", help=f"upstream commit-ish (default {PUBLISHED_REF})")
    parser.add_argument("--write", action="store_true", help="apply the refresh")
    parser.add_argument("--repository", help="upstream https URL (first import only)")
    parser.add_argument("--root", type=Path, default=None, help="skill-craft checkout (default: this script's)")
    args = parser.parse_args(argv)
    refresh_flags = (args.source, args.ref, args.write, args.repository)
    if args.check and any(refresh_flags):
        raise Failure(64, "--check is offline and takes only --bundle and --root")
    if not args.check and not args.source:
        raise Failure(64, "choose --check or --bundle NAME --from DIR")
    if args.source and not args.bundle:
        raise Failure(64, "--from requires --bundle NAME")
    if args.bundle is not None and not NAME.fullmatch(args.bundle):
        raise Failure(64, f"invalid bundle name: {args.bundle!r}")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse(argv)
        root = (args.root or default_root()).resolve()
        if args.check:
            return run_check(root, args.bundle)
        return refresh(args, root)
    except Failure as exc:
        print(f"sync-vendored-bundles: {exc.message}", file=sys.stderr)
        return exc.code
    except SystemExit as exc:  # argparse --help
        return int(exc.code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
