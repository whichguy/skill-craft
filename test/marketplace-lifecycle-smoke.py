#!/usr/bin/env python3
"""Run an explicit, disposable marketplace lifecycle check against native CLIs.

The harness creates a unique harmless fixture, verifies a v1 install, publishes
v2, verifies one fresh v2 discovery with its exact skill-card bytes, then
uninstalls it. It is intentionally absent from test/run-all.sh and CI because
it invokes installed Claude, Grok, or Codex CLIs.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import threading
import uuid
from typing import Any, Iterable


CLT_GIT = Path("/Library/Developer/CommandLineTools/usr/bin/git")
PAYLOAD_KEY = "SKILL_CRAFT_E2E_PAYLOAD"
HOSTS = ("claude", "grok", "codex")
HOME_PATH = str(Path.home())
BASE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR", "DEVELOPER_DIR")
CODEX_ENV_KEYS = ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", *BASE_ENV_KEYS)


class VerificationError(RuntimeError):
    """A required native-host assertion did not hold."""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sanitize(text: str) -> str:
    """Keep command evidence useful without retaining user paths or token-like text."""
    if HOME_PATH:
        text = text.replace(HOME_PATH, "$USER_HOME")
    text = re.sub(r"(?i)(bearer\s+)[\w.+/=-]+", r"\1[REDACTED]", text)
    return re.sub(
        r"\b(?:sk-[A-Za-z0-9_-]{12,}|xai-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})",
        "[REDACTED]",
        text,
    )


def receipt_text(text: str, limit: int = 12_000) -> str:
    safe = sanitize(text)
    if len(safe) <= limit:
        return safe
    return (
        safe[:limit]
        + f"\\n[truncated; sha256={sha256_bytes(safe.encode()):s} bytes={len(safe)}]\\n"
    )


def collect_sanitized_stream(stream: Any, limit: int = 12_000) -> str:
    """Drain a text stream without writing its raw contents to disk."""
    pieces: list[str] = []
    retained = 0
    truncated = False
    for line in stream:
        safe = sanitize(line)
        remaining = limit - retained
        if remaining <= 0:
            truncated = True
            continue
        if len(safe) > remaining:
            pieces.append(safe[:remaining])
            retained += remaining
            truncated = True
            continue
        pieces.append(safe)
        retained += len(safe)
    if truncated:
        pieces.append("\n[truncated sanitized stderr after 12000 characters]\n")
    return "".join(pieces)


def safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize(value)
    if isinstance(value, list):
        return [safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): safe_value(item) for key, item in value.items()}
    return value


def require_clt_git() -> str:
    if not CLT_GIT.is_file() or not os.access(CLT_GIT, os.X_OK):
        raise VerificationError(
            "Command Line Tools git is required at " + sanitize(str(CLT_GIT))
        )
    return str(CLT_GIT)


def command_environment(host: str | None = None, profile: Path | None = None) -> dict[str, str]:
    """Build a credential-free profile environment without assigning HOME/CODEX_HOME."""
    env = {key: os.environ[key] for key in BASE_ENV_KEYS if key in os.environ}
    existing_path = env.get("PATH", "")
    env["PATH"] = str(CLT_GIT.parent) + (os.pathsep + existing_path if existing_path else "")
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "NO_COLOR": "1",
        }
    )
    if host == "claude":
        if profile is None:
            raise ValueError("Claude requires a disposable profile")
        env["CLAUDE_CONFIG_DIR"] = str(profile)
    elif host == "grok":
        if profile is None:
            raise ValueError("Grok requires a disposable profile")
        env["GROK_HOME"] = str(profile)
        env["GROK_CLAUDE_SKILLS_ENABLED"] = "false"
        env["GROK_CURSOR_SKILLS_ENABLED"] = "false"
    elif host is not None:
        raise ValueError(f"unsupported isolated host: {host}")
    return env


def codex_environment() -> dict[str, str]:
    """Use an allowlist while forwarding the existing on-disk config location unchanged."""
    env = {key: os.environ[key] for key in CODEX_ENV_KEYS if key in os.environ}
    existing_path = env.get("PATH", "")
    env["PATH"] = str(CLT_GIT.parent) + (os.pathsep + existing_path if existing_path else "")
    env["NO_COLOR"] = "1"
    return env


def host_binary(host: str) -> str:
    candidates = {
        "claude": (Path.home() / ".claude" / "tools" / "claude", shutil.which("claude")),
        "grok": (Path.home() / ".grok" / "bin" / "grok", shutil.which("grok")),
        "codex": (shutil.which("codex"),),
    }
    for candidate in candidates[host]:
        if candidate and os.access(candidate, os.X_OK):
            return str(candidate)
    raise VerificationError(f"{host} CLI is unavailable on PATH")


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    receipts: list[dict[str, Any]],
    label: str,
    timeout: int = 90,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        receipts.append(
            {
                "label": label,
                "argv": [sanitize(value) for value in argv],
                "cwd": sanitize(str(cwd)),
                "timeout_seconds": timeout,
                "stdout": receipt_text(error.stdout or ""),
                "stderr": receipt_text(error.stderr or ""),
            }
        )
        raise VerificationError(f"{label} timed out after {timeout}s") from error
    receipts.append(
        {
            "label": label,
            "argv": [sanitize(value) for value in argv],
            "cwd": sanitize(str(cwd)),
            "exit": result.returncode,
            "stdout": receipt_text(result.stdout),
            "stderr": receipt_text(result.stderr),
        }
    )
    if result.returncode and not allow_failure:
        raise VerificationError(
            f"{label} failed with exit {result.returncode}: "
            f"{sanitize(result.stderr or result.stdout).strip()}"
        )
    return result


def git_command(
    argv: list[str], *, cwd: Path, receipts: list[dict[str, Any]], label: str
) -> subprocess.CompletedProcess[str]:
    return run_command(
        [require_clt_git(), *argv],
        cwd=cwd,
        env=command_environment(),
        receipts=receipts,
        label=label,
    )


def parse_json(result: subprocess.CompletedProcess[str], label: str) -> Any:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError(f"{label} did not emit JSON: {error}") from error


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def inventory_rows(value: Any, plugin_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in walk_dicts(value):
        identifiers = (row.get("name"), row.get("id"), row.get("pluginId"))
        matches = any(
            item == plugin_name
            or (isinstance(item, str) and item.startswith(plugin_name + "@"))
            for item in identifiers
        )
        if matches and ("version" in row or "pluginId" in row or "id" in row):
            rows.append(row)
    return rows


def assert_inventory_version(
    value: Any, *, plugin_name: str, version: str, label: str
) -> list[dict[str, Any]]:
    rows = inventory_rows(value, plugin_name)
    matches = [row for row in rows if str(row.get("version")) == version]
    if len(matches) != 1:
        raise VerificationError(
            f"{label} expected exactly one {plugin_name} at {version}; observed={safe_value(rows)}"
        )
    return rows


def assert_absent(value: Any, *, plugin_name: str, label: str) -> None:
    rows = inventory_rows(value, plugin_name)
    if rows:
        raise VerificationError(f"{label} still lists {plugin_name}: {safe_value(rows)}")


def fixture_manifest(name: str, version: str) -> dict[str, Any]:
    return {
        "name": name,
        "version": version,
        "description": "Disposable lifecycle fixture; no commands, hooks, MCP, or network behavior.",
        "author": {"name": "Skill Craft E2E"},
        "license": "MIT",
    }


def fixture_card(name: str, version: str, payload: str) -> str:
    return f"""---
name: {name}
description: Disposable marketplace lifecycle fixture. It has no runtime behavior.
version: {version}
---

# Disposable lifecycle fixture

{PAYLOAD_KEY}: {payload}
"""


def write_fixture(
    worktree: Path,
    *,
    market_name: str,
    plugin_name: str,
    version: str,
    payload: str,
) -> None:
    plugin = worktree / "plugins" / plugin_name
    manifest = fixture_manifest(plugin_name, version)
    write_text(plugin / ".claude-plugin" / "plugin.json", json.dumps(manifest, indent=2) + "\n")
    write_text(plugin / ".codex-plugin" / "plugin.json", json.dumps({**manifest, "skills": "./skills"}, indent=2) + "\n")
    write_text(plugin / "skills" / plugin_name / "SKILL.md", fixture_card(plugin_name, version, payload))
    write_text(
        worktree / ".claude-plugin" / "marketplace.json",
        json.dumps(
            {
                "name": market_name,
                "owner": {"name": "Skill Craft E2E"},
                "plugins": [{"name": plugin_name, "source": f"./plugins/{plugin_name}"}],
            },
            indent=2,
        )
        + "\n",
    )
    write_text(
        worktree / ".grok-plugin" / "marketplace.json",
        json.dumps(
            {
                "name": market_name,
                "description": "Disposable lifecycle marketplace fixture.",
                "owner": {"name": "Skill Craft E2E"},
                "plugins": [
                    {
                        "name": plugin_name,
                        "version": version,
                        "description": "Disposable lifecycle fixture.",
                        "category": "productivity",
                        "source": {"type": "local", "path": f"./plugins/{plugin_name}"},
                    }
                ],
            },
            indent=2,
        )
        + "\n",
    )
    write_text(
        worktree / ".agents" / "plugins" / "marketplace.json",
        json.dumps(
            {
                "name": market_name,
                "plugins": [
                    {
                        "name": plugin_name,
                        "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                        "category": "Productivity",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
    )


def make_fixture_repository(
    root: Path, *, market_name: str, plugin_name: str, receipts: list[dict[str, Any]]
) -> tuple[Path, Path, str]:
    origin = root / "fixture-origin.git"
    worktree = root / "fixture-worktree"
    git_command(["init", "--bare", str(origin)], cwd=root, receipts=receipts, label="fixture.git.init")
    git_command(["clone", str(origin), str(worktree)], cwd=root, receipts=receipts, label="fixture.git.clone")
    write_fixture(worktree, market_name=market_name, plugin_name=plugin_name, version="1.0.0", payload="v1")
    git_command(["add", "."], cwd=worktree, receipts=receipts, label="fixture.git.add-v1")
    git_command(
        ["-c", "user.name=Skill Craft E2E", "-c", "user.email=e2e@invalid", "commit", "-m", "fixture v1"],
        cwd=worktree,
        receipts=receipts,
        label="fixture.git.commit-v1",
    )
    git_command(["branch", "-M", "main"], cwd=worktree, receipts=receipts, label="fixture.git.branch-main")
    git_command(
        ["-c", "protocol.file.allow=always", "push", "-u", "origin", "main"],
        cwd=worktree,
        receipts=receipts,
        label="fixture.git.push-v1",
    )
    git_command(
        ["--git-dir", str(origin), "symbolic-ref", "HEAD", "refs/heads/main"],
        cwd=worktree,
        receipts=receipts,
        label="fixture.git.set-origin-head",
    )
    v1 = git_command(["rev-parse", "HEAD"], cwd=worktree, receipts=receipts, label="fixture.git.rev-v1")
    return origin, worktree, v1.stdout.strip()


def publish_v2(
    worktree: Path, *, market_name: str, plugin_name: str, receipts: list[dict[str, Any]]
) -> str:
    write_fixture(worktree, market_name=market_name, plugin_name=plugin_name, version="1.0.1", payload="v2")
    git_command(["add", "."], cwd=worktree, receipts=receipts, label="fixture.git.add-v2")
    git_command(
        ["-c", "user.name=Skill Craft E2E", "-c", "user.email=e2e@invalid", "commit", "-m", "fixture v2"],
        cwd=worktree,
        receipts=receipts,
        label="fixture.git.commit-v2",
    )
    git_command(
        ["-c", "protocol.file.allow=always", "push", "origin", "main"],
        cwd=worktree,
        receipts=receipts,
        label="fixture.git.push-v2",
    )
    result = git_command(["rev-parse", "HEAD"], cwd=worktree, receipts=receipts, label="fixture.git.rev-v2")
    return result.stdout.strip()


def cache_cards(host: str, profile: Path, plugin_name: str) -> list[Path]:
    cache = profile / ("plugins/cache" if host == "claude" else "installed-plugins")
    if not cache.exists():
        return []
    return sorted(
        path
        for path in cache.rglob("SKILL.md")
        if path.parent.name == plugin_name and path.parent.parent.name == "skills"
    )


def owned_cache_state(cache_root: Path) -> dict[str, Any]:
    """Describe only the uniquely named fixture cache; never remove it here."""
    if not cache_root.exists():
        return {"path": str(cache_root), "exists": False, "entries": []}
    entries = [
        str(path.relative_to(cache_root))
        for path in sorted(cache_root.rglob("*"))[:20]
    ]
    return {"path": str(cache_root), "exists": True, "entries": entries}


def assert_installed_card(
    *, host: str, profile: Path, plugin_name: str, expected: Path, payload: str
) -> dict[str, Any]:
    cards = cache_cards(host, profile, plugin_name)
    expected_sha = sha256_file(expected)
    matches = [card for card in cards if sha256_file(card) == expected_sha]
    if len(matches) != 1:
        observed = [{"path": str(card), "sha256": sha256_file(card)} for card in cards]
        raise VerificationError(
            f"expected one installed {payload} card for {plugin_name}; observed={safe_value(observed)}"
        )
    if f"{PAYLOAD_KEY}: {payload}" not in matches[0].read_text(encoding="utf-8"):
        raise VerificationError(f"installed card lacks {payload} marker")
    return {
        "expected_sha256": expected_sha,
        "installed_sha256": sha256_file(matches[0]),
        "installed_card": str(matches[0]),
        "matching_card_count": len(matches),
    }


def remove_profile(profile: Path, host_dir: Path) -> None:
    if profile.parent != host_dir or profile.name != "profile" or profile.is_symlink():
        raise VerificationError(f"refusing to remove unexpected profile path: {sanitize(str(profile))}")
    if profile.exists():
        shutil.rmtree(profile)
    if profile.exists():
        raise VerificationError(f"disposable profile still exists after cleanup: {sanitize(str(profile))}")


def host_command(host: str, binary: str, leader_socket: Path, parts: list[str]) -> list[str]:
    if host == "grok":
        return [binary, "--leader-socket", str(leader_socket), "plugin", *parts]
    return [binary, "plugin", *parts]


def lifecycle_claude_or_grok(
    *, host: str, host_dir: Path, token: str, keep_profile: bool
) -> dict[str, Any]:
    profile = host_dir / "profile"
    project = host_dir / "consumer-project"
    profile.mkdir(parents=True)
    project.mkdir()
    sentinel = profile / "consumer-state-sentinel.json"
    sentinel_bytes = b'{"owner":"consumer","state":"preserve-me"}\n'
    sentinel.write_bytes(sentinel_bytes)
    sentinel_hash = sha256_file(sentinel)
    receipts: list[dict[str, Any]] = []
    market_name = f"skill-craft-e2e-{host}-{token}"
    plugin_name = f"skill-craft-e2e-{host}-plugin-{token}"
    binary = host_binary(host)
    env = command_environment(host, profile)
    leader_socket = profile / "leader-e2e.sock"
    cleanup_needed = False
    failure: Exception | None = None
    result: dict[str, Any] = {
        "host": host,
        "fixture": {"marketplace": market_name, "plugin": plugin_name},
        "isolation": {
            "profile_variable": "CLAUDE_CONFIG_DIR" if host == "claude" else "GROK_HOME",
            "consumer_state_sentinel_sha256": sentinel_hash,
        },
    }

    def call(parts: list[str], label: str, *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
        return run_command(
            host_command(host, binary, leader_socket, parts),
            cwd=project,
            env=env,
            receipts=receipts,
            label=label,
            allow_failure=allow_failure,
        )

    try:
        version = run_command([binary, "--version"], cwd=project, env=env, receipts=receipts, label="host.version")
        origin, worktree, v1_commit = make_fixture_repository(
            host_dir, market_name=market_name, plugin_name=plugin_name, receipts=receipts
        )
        source = str(worktree) if host == "claude" else origin.as_uri()
        call(["marketplace", "add", source], "marketplace.add-v1")
        available_v1 = parse_json(call(["list", "--available", "--json"], "inventory.available-v1"), "inventory.available-v1")

        install = ["install", f"{plugin_name}@{market_name}", "--json"] if host == "claude" else ["install", plugin_name, "--trust"]
        cleanup_needed = True
        call(install, "plugin.install-v1")
        installed_v1 = parse_json(call(["list", "--json"], "inventory.installed-v1"), "inventory.installed-v1")
        assert_inventory_version(installed_v1, plugin_name=plugin_name, version="1.0.0", label="inventory.installed-v1")
        card_v1 = assert_installed_card(
            host=host,
            profile=profile,
            plugin_name=plugin_name,
            expected=worktree / "plugins" / plugin_name / "skills" / plugin_name / "SKILL.md",
            payload="v1",
        )

        v2_commit = publish_v2(worktree, market_name=market_name, plugin_name=plugin_name, receipts=receipts)
        marketplace_update = ["marketplace", "update", market_name] if host == "claude" else ["marketplace", "update", origin.stem]
        call(marketplace_update, "marketplace.update-v2")
        available_v2 = parse_json(call(["list", "--available", "--json"], "inventory.available-v2-fresh"), "inventory.available-v2-fresh")
        update = ["update", f"{plugin_name}@{market_name}", "--json"] if host == "claude" else ["update", plugin_name]
        call(update, "plugin.update-v2")
        installed_v2 = parse_json(call(["list", "--json"], "inventory.installed-v2-fresh"), "inventory.installed-v2-fresh")
        assert_inventory_version(installed_v2, plugin_name=plugin_name, version="1.0.1", label="inventory.installed-v2-fresh")
        card_v2 = assert_installed_card(
            host=host,
            profile=profile,
            plugin_name=plugin_name,
            expected=worktree / "plugins" / plugin_name / "skills" / plugin_name / "SKILL.md",
            payload="v2",
        )

        remove = ["uninstall", f"{plugin_name}@{market_name}", "--json"] if host == "claude" else ["uninstall", plugin_name, "--confirm"]
        call(remove, "plugin.uninstall")
        cleanup_needed = False
        after_remove = parse_json(call(["list", "--json"], "inventory.after-uninstall-fresh"), "inventory.after-uninstall-fresh")
        assert_absent(after_remove, plugin_name=plugin_name, label="inventory.after-uninstall-fresh")
        remaining_cards = cache_cards(host, profile, plugin_name)
        if remaining_cards:
            raise VerificationError(
                f"uninstall left fixture cache cards: {safe_value([str(card) for card in remaining_cards])}"
            )
        if not sentinel.is_file() or sentinel.read_bytes() != sentinel_bytes or sha256_file(sentinel) != sentinel_hash:
            raise VerificationError("consumer-state sentinel changed or disappeared")
        result.update(
            {
                "status": "passed",
                "host_version": version.stdout.strip(),
                "fixture": {
                    **result["fixture"],
                    "source": source,
                    "v1_commit": v1_commit,
                    "v2_commit": v2_commit,
                },
                "assertions": {
                    "available_v1_recorded": bool(inventory_rows(available_v1, plugin_name)),
                    "v1_installed_card": card_v1,
                    "available_v2_recorded_before_update": bool(inventory_rows(available_v2, plugin_name)),
                    "v2_installed_inventory_exactly_once": True,
                    "v2_installed_card": card_v2,
                    "uninstall_removed_inventory_entry": True,
                    "fixture_cache_cards_absent_after_uninstall": True,
                    "consumer_state_sentinel_preserved": True,
                },
            }
        )
    except Exception as error:  # Evidence and owned cleanup must still be written.
        failure = error
    finally:
        if cleanup_needed:
            try:
                cleanup = call(
                    ["uninstall", f"{plugin_name}@{market_name}", "--json"] if host == "claude" else ["uninstall", plugin_name, "--confirm"],
                    "cleanup.plugin.uninstall",
                    allow_failure=True,
                )
                if cleanup.returncode:
                    result["cleanup_error"] = f"plugin cleanup exited {cleanup.returncode}"
                    if failure is None:
                        failure = VerificationError(result["cleanup_error"])
            except Exception as cleanup_error:
                result["cleanup_error"] = sanitize(str(cleanup_error))
                if failure is None:
                    failure = cleanup_error
        post_cleanup_cards = cache_cards(host, profile, plugin_name)
        result["isolation"]["fixture_cache_after_cleanup"] = {
            "matching_card_count": len(post_cleanup_cards),
            "cards": [str(card) for card in post_cleanup_cards],
        }
        if post_cleanup_cards and failure is None:
            failure = VerificationError("fixture cache cards remained after uninstall cleanup")
        if not keep_profile:
            result["isolation"]["profile_disposed"] = False
            try:
                remove_profile(profile, host_dir)
                result["isolation"]["profile_disposed"] = not profile.exists()
            except Exception as cleanup_error:
                result["cleanup_error"] = sanitize(str(cleanup_error))
                if failure is None:
                    failure = cleanup_error
        else:
            result["isolation"]["profile_disposed"] = False
            result["isolation"]["profile_retained_for_diagnosis"] = profile.exists()
        result["commands"] = receipts
        if failure is not None:
            result.update({"status": "failed", "error": sanitize(str(failure))})
    return result


def toml_string(value: str) -> str:
    """JSON strings are valid TOML basic strings for the values used here."""
    return json.dumps(value)


def codex_config_args(market_name: str, market_root: Path, identity: str, *, enable_plugin: bool) -> list[str]:
    args = [
        "-c",
        f"marketplaces.{market_name}.source_type=\"local\"",
        "-c",
        f"marketplaces.{market_name}.source={toml_string(str(market_root))}",
    ]
    if enable_plugin:
        # Do not use plugins."name@market".enabled=true: this CLI treats that
        # quoted dotted segment literally. One inline table preserves the ID.
        args.extend(["-c", f"plugins={{{toml_string(identity)}={{enabled=true}}}}"])
    return args


def config_snapshot() -> dict[str, Any]:
    config = Path.home() / ".codex" / "config.toml"
    if not config.exists():
        return {"exists": False, "sha256": None, "top_level_value_sha256": {}}
    raw = config.read_bytes()
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise VerificationError("cannot compare Codex config semantics: " + sanitize(str(error))) from error
    return {
        "exists": True,
        "sha256": sha256_bytes(raw),
        "top_level_value_sha256": {
            key: sha256_bytes(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))
            for key, value in parsed.items()
        },
    }


def scan_codex_skills(
    *,
    binary: str,
    config_args: list[str],
    cwd: Path,
    env: dict[str, str],
    receipts: list[dict[str, Any]],
    label: str,
    plugin_name: str,
    identity: str,
) -> list[dict[str, Any]]:
    argv = [binary, *config_args, "app-server", "--stdio"]
    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
    except OSError as error:
        receipts.append(
            {
                "label": label,
                "argv": [sanitize(value) for value in argv],
                "cwd": sanitize(str(cwd)),
                "exit": None,
                "stderr": receipt_text(str(error)),
            }
        )
        raise VerificationError(f"{label} could not start app server: {sanitize(str(error))}") from error
    stderr_output: list[str] = []

    def drain_stderr() -> None:
        assert proc.stderr is not None
        stderr_output.append(collect_sanitized_stream(proc.stderr))

    stderr_thread = threading.Thread(target=drain_stderr, name=f"{label}-stderr", daemon=True)
    stderr_thread.start()
    protocol: list[dict[str, Any]] = []
    completed = False

    def request(request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(json.dumps({"id": request_id, "method": method, "params": params}) + "\n")
        proc.stdin.flush()
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            ready, _, _ = select.select([proc.stdout], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                break
            line = proc.stdout.readline()
            if not line:
                raise VerificationError(f"{label} app server exited before {method}")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as error:
                raise VerificationError(f"{label} app server emitted invalid JSON") from error
            protocol.append({"id": message.get("id"), "has_error": "error" in message})
            if message.get("id") == request_id:
                return message
        raise VerificationError(f"{label} app server timed out on {method}")

    try:
        initialized = request(
            1,
            "initialize",
            {
                "clientInfo": {"name": "skill-craft-marketplace-e2e", "version": "1.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        if "error" in initialized:
            raise VerificationError(f"{label} app server initialize failed: {safe_value(initialized['error'])}")
        assert proc.stdin is not None
        proc.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        proc.stdin.flush()
        response = request(2, "skills/list", {"cwds": [str(cwd)], "forceReload": True})
        if "error" in response:
            raise VerificationError(f"{label} skills/list failed: {safe_value(response['error'])}")
        data = response.get("result", {}).get("data", [])
        skills = [
            skill
            for group in data
            if isinstance(group, dict)
            for skill in group.get("skills", [])
            if isinstance(skill, dict)
            and (skill.get("name") == plugin_name or skill.get("pluginId") == identity)
        ]
        completed = True
        return skills
    finally:
        if proc.stdin is not None and not proc.stdin.closed:
            proc.stdin.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        stderr_thread.join()
        if proc.stdout is not None:
            proc.stdout.close()
        receipts.append(
            {
                "label": label,
                "argv": [sanitize(value) for value in argv],
                "cwd": sanitize(str(cwd)),
                "exit": 0 if completed else proc.returncode,
                "app_server_elapsed_seconds": round(time.monotonic() - started, 3),
                "skill_match_count": len(skills) if completed else 0,
                "stderr": stderr_output[0] if stderr_output else "",
                "protocol_events": protocol,
            }
        )


def assert_codex_skill(
    skills: list[dict[str, Any]], *, expected: Path, payload: str, label: str
) -> dict[str, Any]:
    if len(skills) != 1:
        raise VerificationError(f"{label} expected exactly one runtime skill; saw {safe_value(skills)}")
    path_value = skills[0].get("path")
    if not isinstance(path_value, str):
        raise VerificationError(f"{label} runtime skill has no path")
    installed = Path(path_value)
    expected_sha = sha256_file(expected)
    if not installed.is_file() or sha256_file(installed) != expected_sha:
        raise VerificationError(f"{label} runtime skill bytes do not match the fixture")
    if f"{PAYLOAD_KEY}: {payload}" not in installed.read_text(encoding="utf-8"):
        raise VerificationError(f"{label} runtime skill lacks {payload} marker")
    return {
        "expected_sha256": expected_sha,
        "runtime_sha256": sha256_file(installed),
        "runtime_card": str(installed),
        "matching_card_count": 1,
    }


def lifecycle_codex(*, host_dir: Path, token: str) -> dict[str, Any]:
    host = "codex"
    project = host_dir / "consumer-project"
    project.mkdir(parents=True)
    sentinel = project / "consumer-state-sentinel.json"
    sentinel_bytes = b'{"owner":"consumer","state":"preserve-me"}\n'
    sentinel.write_bytes(sentinel_bytes)
    sentinel_hash = sha256_file(sentinel)
    receipts: list[dict[str, Any]] = []
    market_name = f"skill-craft-e2e-codex-{token}"
    plugin_name = f"skill-craft-e2e-codex-plugin-{token}"
    identity = f"{plugin_name}@{market_name}"
    cache_root = Path.home() / ".codex" / "plugins" / "cache" / market_name / plugin_name
    binary = host_binary(host)
    env = codex_environment()
    before_config = config_snapshot()
    cleanup_needed = False
    failure: Exception | None = None
    result: dict[str, Any] = {
        "host": host,
        "fixture": {"marketplace": market_name, "plugin": plugin_name, "plugin_id": identity},
        "isolation": {
            "marketplace_source": "command-scoped local config",
            "native_plugin_cleanup": "plugin remove unique-plugin@unique-marketplace",
            "consumer_state_sentinel_sha256": sentinel_hash,
            "config_before": before_config,
            "fixture_cache_before": owned_cache_state(cache_root),
        },
    }

    def args(*, enable_plugin: bool) -> list[str]:
        return codex_config_args(market_name, worktree, identity, enable_plugin=enable_plugin)

    def call(parts: list[str], label: str, *, enable_plugin: bool = False, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
        return run_command(
            [binary, *args(enable_plugin=enable_plugin), *parts],
            cwd=project,
            env=env,
            receipts=receipts,
            label=label,
            allow_failure=allow_failure,
        )

    try:
        version = run_command([binary, "--version"], cwd=project, env=env, receipts=receipts, label="host.version")
        _, worktree, v1_commit = make_fixture_repository(
            host_dir, market_name=market_name, plugin_name=plugin_name, receipts=receipts
        )
        if cache_root.exists():
            raise VerificationError("unique Codex fixture cache already exists before install")
        available_v1 = parse_json(
            call(["plugin", "list", "--marketplace", market_name, "--available", "--json"], "inventory.available-v1"),
            "inventory.available-v1",
        )
        assert_inventory_version(available_v1, plugin_name=plugin_name, version="1.0.0", label="inventory.available-v1")
        cleanup_needed = True
        call(["plugin", "add", identity, "--json"], "plugin.add-v1", enable_plugin=True)
        installed_v1 = parse_json(
            call(["plugin", "list", "--marketplace", market_name, "--json"], "inventory.installed-v1", enable_plugin=True),
            "inventory.installed-v1",
        )
        assert_inventory_version(installed_v1, plugin_name=plugin_name, version="1.0.0", label="inventory.installed-v1")
        skill_v1 = assert_codex_skill(
            scan_codex_skills(
                binary=binary,
                config_args=args(enable_plugin=True),
                cwd=project,
                env=env,
                receipts=receipts,
                label="runtime.v1-fresh",
                plugin_name=plugin_name,
                identity=identity,
            ),
            expected=worktree / "plugins" / plugin_name / "skills" / plugin_name / "SKILL.md",
            payload="v1",
            label="runtime.v1-fresh",
        )

        v2_commit = publish_v2(worktree, market_name=market_name, plugin_name=plugin_name, receipts=receipts)
        call(["plugin", "add", identity, "--json"], "plugin.add-v2", enable_plugin=True)
        installed_v2 = parse_json(
            call(["plugin", "list", "--marketplace", market_name, "--json"], "inventory.installed-v2-fresh", enable_plugin=True),
            "inventory.installed-v2-fresh",
        )
        assert_inventory_version(installed_v2, plugin_name=plugin_name, version="1.0.1", label="inventory.installed-v2-fresh")
        skill_v2 = assert_codex_skill(
            scan_codex_skills(
                binary=binary,
                config_args=args(enable_plugin=True),
                cwd=project,
                env=env,
                receipts=receipts,
                label="runtime.v2-fresh",
                plugin_name=plugin_name,
                identity=identity,
            ),
            expected=worktree / "plugins" / plugin_name / "skills" / plugin_name / "SKILL.md",
            payload="v2",
            label="runtime.v2-fresh",
        )

        call(["plugin", "remove", identity, "--json"], "plugin.remove", allow_failure=False)
        cleanup_needed = False
        after_remove = parse_json(
            call(["plugin", "list", "--marketplace", market_name, "--json"], "inventory.after-remove-fresh"),
            "inventory.after-remove-fresh",
        )
        assert_absent(after_remove, plugin_name=plugin_name, label="inventory.after-remove-fresh")
        removed = scan_codex_skills(
            binary=binary,
            config_args=args(enable_plugin=False),
            cwd=project,
            env=env,
            receipts=receipts,
            label="runtime.after-remove-fresh",
            plugin_name=plugin_name,
            identity=identity,
        )
        if removed:
            raise VerificationError(f"runtime.after-remove-fresh still found {safe_value(removed)}")
        cache_after_remove = owned_cache_state(cache_root)
        result["isolation"]["fixture_cache_after_remove"] = cache_after_remove
        if cache_after_remove["exists"]:
            raise VerificationError(
                f"native removal left unique fixture cache: {safe_value(cache_after_remove)}"
            )
        if not sentinel.is_file() or sentinel.read_bytes() != sentinel_bytes or sha256_file(sentinel) != sentinel_hash:
            raise VerificationError("consumer-state sentinel changed or disappeared")
        result.update(
            {
                "status": "passed",
                "host_version": version.stdout.strip(),
                "fixture": {**result["fixture"], "v1_commit": v1_commit, "v2_commit": v2_commit},
                "assertions": {
                    "available_v1_exactly_once": True,
                    "v1_runtime_card": skill_v1,
                    "v2_installed_inventory_exactly_once": True,
                    "v2_runtime_card": skill_v2,
                    "uninstall_removed_inventory_entry": True,
                    "runtime_absent_after_remove": True,
                    "fixture_cache_absent_after_remove": True,
                    "consumer_state_sentinel_preserved": True,
                },
            }
        )
    except Exception as error:  # Preserve evidence and clean only the unique native key.
        failure = error
    finally:
        if cleanup_needed:
            try:
                cleanup = call(["plugin", "remove", identity, "--json"], "cleanup.plugin.remove", allow_failure=True)
                if cleanup.returncode:
                    result["cleanup_error"] = f"plugin cleanup exited {cleanup.returncode}"
                    if failure is None:
                        failure = VerificationError(result["cleanup_error"])
            except Exception as cleanup_error:
                result["cleanup_error"] = sanitize(str(cleanup_error))
                if failure is None:
                    failure = cleanup_error
        cache_after_cleanup = owned_cache_state(cache_root)
        result["isolation"]["fixture_cache_after_cleanup"] = cache_after_cleanup
        if cache_after_cleanup["exists"] and failure is None:
            failure = VerificationError(
                f"unique fixture cache remains after cleanup: {safe_value(cache_after_cleanup)}"
            )
        try:
            after_config = config_snapshot()
            result["isolation"]["config_after"] = after_config
            result["isolation"]["config_semantics_preserved"] = after_config == before_config
            if after_config != before_config and failure is None:
                failure = VerificationError("Codex config semantics changed during lifecycle")
        except Exception as error:
            result["cleanup_error"] = sanitize(str(error))
            if failure is None:
                failure = error
        result["commands"] = receipts
        if failure is not None:
            result.update({"status": "failed", "error": sanitize(str(failure))})
    return result


def report_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Marketplace lifecycle smoke evidence",
        "",
        "This is an opt-in native-CLI fixture test. It creates a local Git marketplace, checks v1 to v2 lifecycle behavior, and uses no model invocation.",
        "",
        "| Host | Result | Upgrade | Fresh discovery | Removal | Consumer state |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        if result.get("status") == "passed":
            fixture = result["fixture"]
            upgrade = f"`{fixture.get('v1_commit', '')[:12]}` to `{fixture.get('v2_commit', '')[:12]}`"
            lines.append(f"| {result['host']} | passed | {upgrade} | exact one v2 | absent | preserved |")
        else:
            lines.append(f"| {result['host']} | failed | — | — | — | — |")
    lines.extend(
        [
            "",
            "`results.json` contains sanitized command receipts and hashes. This test does not prove model selection, model output, authentication, quota, or a production marketplace release.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_self_test() -> int:
    """Exercise redaction, environment isolation, and owned cleanup without a host CLI."""
    raw = "Bearer bearer-secret-123456 sk-abcdefghijklmnop xai-abcdefghijklmnop github_pat_abcdefghijklmnop\n"
    safe = sanitize(raw)
    if (
        "bearer-secret-123456" in safe
        or "sk-abcdefghijklmnop" in safe
        or "xai-abcdefghijklmnop" in safe
        or "github_pat_abcdefghijklmnop" in safe
    ):
        raise VerificationError("sanitize did not redact representative credential-shaped text")
    if "Bearer [REDACTED]" not in safe:
        raise VerificationError("sanitize did not preserve and redact a Bearer value")
    stream_safe = collect_sanitized_stream(io.StringIO(raw))
    if stream_safe != safe:
        raise VerificationError("stream stderr sanitization diverged from direct sanitization")

    ambient_key = "SKILL_CRAFT_E2E_AMBIENT_SECRET"
    had_ambient = ambient_key in os.environ
    old_ambient = os.environ.get(ambient_key)
    os.environ[ambient_key] = "must-not-reach-codex-child"
    try:
        env = codex_environment()
    finally:
        if had_ambient:
            assert old_ambient is not None
            os.environ[ambient_key] = old_ambient
        else:
            del os.environ[ambient_key]
    unexpected = set(env) - (set(CODEX_ENV_KEYS) | {"NO_COLOR"})
    if unexpected or ambient_key in env or "CODEX_HOME" in env:
        raise VerificationError(f"Codex child environment was not minimized: {sorted(unexpected)}")
    if "HOME" in os.environ and env.get("HOME") != os.environ["HOME"]:
        raise VerificationError("Codex child HOME was changed instead of forwarded unchanged")

    with tempfile.TemporaryDirectory(prefix="skill-craft-lifecycle-self-test-") as temp:
        root = Path(temp)
        host_dir = root / "claude"
        profile = host_dir / "profile"
        profile.mkdir(parents=True)
        write_text(profile / "consumer-state-sentinel", "preserve\n")
        remove_profile(profile, host_dir)
        if profile.exists():
            raise VerificationError("profile disposal self-test left its profile behind")

        cache_root = root / "unique-fixture-cache"
        if owned_cache_state(cache_root)["exists"]:
            raise VerificationError("empty fixture cache unexpectedly exists")
        write_text(cache_root / "v1" / "SKILL.md", "fixture\n")
        residual = owned_cache_state(cache_root)
        if not residual["exists"] or not residual["entries"]:
            raise VerificationError("fixture cache residual self-test did not detect an owned cache")
        receipt = root / "sanitized-stderr.txt"
        write_text(receipt, stream_safe)
        if "bearer-secret-123456" in receipt.read_text(encoding="utf-8"):
            raise VerificationError("sanitized stderr self-test wrote raw credential-shaped text")

    print(json.dumps({"self_test": "passed", "checks": ["redaction", "env-allowlist", "profile-disposal", "cache-residual"]}))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=(*HOSTS, "all"), help="native host lane to exercise")
    parser.add_argument("--output", type=Path, help="new directory for sanitized evidence and disposable fixtures")
    parser.add_argument("--self-test", action="store_true", help="run no-host redaction and owned-cleanup checks")
    parser.add_argument(
        "--keep-profile",
        action="store_true",
        help="retain only Claude/Grok disposable profiles for diagnosis (default: remove them)",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        if args.host is not None or args.output is not None or args.keep_profile:
            parser.error("--self-test cannot be combined with --host, --output, or --keep-profile")
        return args
    if args.host is None or args.output is None:
        parser.error("--host and --output are required unless --self-test is selected")
    args.output = args.output.expanduser().resolve()
    if args.output.exists():
        parser.error("--output must name a path that does not already exist")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()
    args.output.mkdir(parents=True)
    token = uuid.uuid4().hex[:10]
    selected = HOSTS if args.host == "all" else (args.host,)
    results: list[dict[str, Any]] = []
    for host in selected:
        host_dir = args.output / host
        host_dir.mkdir()
        try:
            result = (
                lifecycle_codex(host_dir=host_dir, token=token)
                if host == "codex"
                else lifecycle_claude_or_grok(host=host, host_dir=host_dir, token=token, keep_profile=args.keep_profile)
            )
        except Exception as error:  # Unexpected errors still receive an evidence result.
            result = {"host": host, "status": "failed", "error": sanitize(str(error))}
        results.append(result)
        write_text(host_dir / "result.json", json.dumps(safe_value(result), indent=2) + "\n")
    write_text(args.output / "results.json", json.dumps(safe_value(results), indent=2) + "\n")
    write_text(args.output / "REPORT.md", report_markdown(results))
    print(json.dumps({"output": sanitize(str(args.output)), "results": safe_value(results)}, indent=2))
    return 0 if all(result.get("status") == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
