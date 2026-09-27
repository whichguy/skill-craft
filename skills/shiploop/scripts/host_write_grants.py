"""Prove the host sandbox allows the writes a tool needs, before it writes anything.

Shared by Ask Agent and ShipLoop. This file is vendored byte-identically as
skills/ask-agent/scripts/host_write_grants.py and
skills/shiploop/scripts/host_write_grants.py; test/host-write-grants.test.py
fails when the copies differ. Edit both together.

Host sandboxes commonly refuse writes outside the working directory: Codex
``workspace-write`` keeps ``.git`` read-only and allows only the working
directory, ``--add-dir`` roots and temp; Grok's ``workspace``/``strict``
profiles and Claude's Bash sandbox allow only the working directory, added
directories and temp. ``require`` tries one real write in each place before
anything is created; ``report`` turns a refusal into one exact, host-first
repair instruction. Evidence: docs/shiploop-grant-preflight-journal.md and
docs/ask-agent-grant-preflight-journal.md.
"""
from __future__ import annotations

import os
import secrets
import shlex
from pathlib import Path
from typing import List, Mapping, NamedTuple, Optional, Sequence, Tuple

EXIT_GRANT_NEEDED = 3


class Product(NamedTuple):
    """How one tool names itself in the repair message."""

    marker: str       # first word of the message, e.g. "SHIPLOOP-GRANT-NEEDED"
    outcome: str      # what did not happen, e.g. "ShipLoop did not start."
    profile: str      # Grok sandbox profile name to suggest
    workarounds: str  # what the agent must not do instead, as one phrase


class GrantError(RuntimeError):
    """The host sandbox refuses a write the tool needs."""

    def __init__(self, blocked: Sequence[Tuple[Path, str, str]], grants: Sequence[Path]):
        self.blocked = list(blocked)
        self.grants = list(grants)
        super().__init__("host sandbox blocks: " + ", ".join(str(path) for path, _, _ in self.blocked))


def _try_write(directory: Path) -> Optional[str]:
    """Create and remove one probe file; return the refusal, or None."""
    if not directory.is_dir():
        return "not a directory"
    probe = directory / f".grant-probe-{secrets.token_hex(4)}"
    try:
        fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        return exc.strerror or type(exc).__name__
    os.close(fd)
    try:
        probe.unlink()
    except OSError as exc:  # created but not removable: still not a usable grant
        return f"cannot remove probe file: {exc.strerror}"
    return None


def nearest_existing(path: Path) -> Path:
    """The directory where creating ``path`` would first write."""
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def require(targets: Sequence[Tuple[Path, str, Path]]) -> None:
    """Probe each (directory, purpose, grant); raise GrantError naming only refused grants.

    ``grant`` is the directory the user should allow when ``directory`` is
    refused: a stable parent rather than one run's own subdirectory.
    """
    blocked, grants = [], []
    for directory, purpose, grant in targets:
        where = nearest_existing(Path(directory).resolve())
        reason = _try_write(where)
        if reason is not None:
            blocked.append((where, purpose, reason))
            resolved = Path(grant).resolve()
            if resolved not in grants:
                grants.append(resolved)
    if blocked:
        raise GrantError(blocked, grants)


def detect_host(environ: Mapping[str, str] = os.environ) -> str:
    """Innermost host first: a nested host inherits its launcher's variables."""
    if environ.get("CODEX_SANDBOX") or environ.get("CODEX_THREAD_ID"):
        return "codex"
    if environ.get("GROK_AGENT") or environ.get("GROK_SESSION_ID") or environ.get("GROK_SANDBOX"):
        return "grok"
    if environ.get("CLAUDECODE"):
        return "claude"
    return "unknown"


def _fixes(grants: Sequence[Path], profile: str) -> List[Tuple[str, str]]:
    quoted = [shlex.quote(str(path)) for path in grants]
    toml = "[" + ", ".join('"' + str(path) + '"' for path in grants) + "]"
    # Codex workspace-write keeps .git read-only even inside cwd; a list probed
    # under another host may omit it, so say so rather than under-grant Codex.
    git_note = ("" if any(path.name == ".git" for path in grants)
                else " plus the repository's .git directory (workspace-write keeps it read-only)")
    return [
        ("claude", "Claude Code - no restart: the user runs "
         + " and ".join(f"/add-dir {q}" for q in quoted)
         + " in this session, then rerun. To persist, list them in permissions.additionalDirectories"
         " in .claude/settings.local.json (Bash sandbox write roots follow these)."),
        ("codex", "Codex - no restart: the user picks Full access in /permissions. Scoped instead"
         f" (restart): codex -c 'sandbox_workspace_write.writable_roots={toml}'{git_note}, or set"
         f" [sandbox_workspace_write] writable_roots = {toml} in ~/.codex/config.toml."),
        ("grok", "Grok - restart required (a sandbox cannot be relaxed mid-session): in"
         f" ~/.grok/sandbox.toml add [profiles.{profile}] extends = \"workspace\" read_write = {toml},"
         f" then relaunch with --sandbox {profile} (or --sandbox off)."),
    ]


def report(error: GrantError, rerun: str, product: Product, environ: Mapping[str, str] = os.environ) -> str:
    """The exact, host-first repair message printed with exit code 3."""
    host = detect_host(environ)
    lines = [
        f"{product.marker}: {product.outcome} This session's sandbox refuses writes it needs.",
        "Blocked:",
    ]
    lines += [f"  - {path}  ({purpose}): {reason}" for path, purpose, reason in error.blocked]
    lines += [
        "Nothing was created; the source checkout is unchanged.",
        "",
        "Repair intent: give THIS session write access to exactly these directories, then rerun",
        "the same command. Grant:",
    ]
    lines += [f"  - {path}" for path in error.grants]
    missing = [path for path in error.grants if not path.exists()]
    if missing:
        lines += ["A grant needs an existing directory; the user first runs, outside this sandbox:",
                  "  mkdir -p " + " ".join(shlex.quote(str(path)) for path in missing)]
    lines += ["", f"Detected host: {host}. How to grant:"]
    fixes = _fixes(error.grants, product.profile)
    fixes.sort(key=lambda row: row[0] != host)
    lines += [f"  * {text}" for _, text in fixes]
    lines += [
        "",
        "Then rerun: " + rerun,
        "",
        "Agent: stop and show the user this message; a grant is the user's decision. Do not work",
        f"around it by {product.workarounds}, or changing sandbox settings yourself.",
    ]
    return "\n".join(lines)
