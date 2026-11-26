#!/usr/bin/env python3
"""Refresh and verify installed skill-craft plugins across hosts after a release.

After `scripts/release.py` cuts a release commit and `scripts/release-push.py`
publishes it to `origin/main`, each installed plugin host needs its own catalog
or package update and an explicit version + skill-inventory read-back (exit
codes alone do not prove the installed plugin moved):

  - Claude Code: `claude plugin marketplace update <mp>` then
    `claude plugin update skill-craft@<mp> --scope user`
  - Codex: check for live runs under `<CODEX_HOME>/plugins/cache/<mp>/skill-craft`,
    then `codex plugin marketplace upgrade <mp>`
  - Antigravity: check for live runs under `<ANTIGRAVITY_PLUGINS_DIR>/skill-craft`,
    then `agy plugin install <antigravity-source>` (replaces in place)
  - Grok (when installed): check for live runs under
    `<GROK_CONFIG_DIR>/installed-plugins/skill-craft*`, then
    `grok plugin marketplace update <mp>` and `grok plugin update skill-craft`
  - Cursor: verifies no shadowing `<CURSOR_CONFIG_DIR>/plugins/local/skill-craft`
    copy exists and confirms Claude Code's `installed_plugins.json` carries the
    expected `skill-craft@<mp>` version for Cursor's automatic import.

Every refreshed (or `--check-only`) host is verified for:
  1. outer `skill-craft` plugin version matching `catalog/skill-craft-plugin.json`,
  2. exact bundled skill leaf inventory matching the release (`skills/*/SKILL.md`),
  3. per-skill frontmatter versions (including `shiploop`) matching the release.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PLUGIN_NAME = "skill-craft"
DEFAULT_MARKETPLACE = "whichguy"
DEFAULT_ANTIGRAVITY_SOURCE = "https://github.com/whichguy/skill-craft/tree/main/plugins/skill-craft"
ALL_HOSTS = ("claude", "codex", "antigravity", "grok", "cursor")
REQUIRED_ALL_HOSTS = frozenset({"claude", "codex", "antigravity"})
FRONT_VERSION = re.compile(r"\A---\n(?:(?!---\n).*\n)*?version:[ \t]*(\S+)[ \t]*\n")


class RefreshError(Exception):
    pass


def card_version(card_path: Path) -> str | None:
    try:
        text = card_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = FRONT_VERSION.match(text)
    return match.group(1) if match else None


def expected_release(repo: Path, *, allow_unreleased: bool) -> dict:
    repo = repo.resolve(strict=True)
    bundle_path = repo / "catalog" / "skill-craft-plugin.json"
    if not bundle_path.is_file():
        raise RefreshError(f"missing {bundle_path}")
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RefreshError(f"unreadable {bundle_path}: {exc}") from exc
    plugin_version = bundle.get("version")
    if not isinstance(plugin_version, str) or not plugin_version.strip():
        raise RefreshError("catalog/skill-craft-plugin.json has no version")

    changes_dir = repo / "changes"
    pending = sorted(
        str(p.relative_to(repo))
        for p in (changes_dir.glob("*/*.md") if changes_dir.is_dir() else ())
    )
    if pending and not allow_unreleased:
        raise RefreshError(
            "pending unreleased change notes in checkout (pass --allow-unreleased to override): "
            + ", ".join(pending)
        )

    sync_script = repo / "scripts" / "sync-plugin-views.sh"
    if sync_script.is_file() and not allow_unreleased:
        sync_check = subprocess.run(
            ["bash", str(sync_script), "--check"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if sync_check.returncode != 0:
            detail = (sync_check.stderr or sync_check.stdout).strip()
            raise RefreshError(
                f"release output is out of sync with source (pass --allow-unreleased to override): {detail}"
            )

    released_skills_root = repo / "plugins" / PLUGIN_NAME / "skills"
    skills_root = released_skills_root if released_skills_root.is_dir() else (repo / "skills")
    skill_versions: dict[str, str] = {}
    for card in sorted(skills_root.glob("*/SKILL.md")):
        ver = card_version(card)
        if not ver:
            raise RefreshError(f"missing frontmatter version in {card.relative_to(repo)}")
        skill_versions[card.parent.name] = ver
    if not skill_versions:
        raise RefreshError(f"no skills found under {skills_root}")
    if "shiploop" not in skill_versions:
        raise RefreshError("expected bundled skill 'shiploop' in release skill inventory")

    return {
        "repo": str(repo),
        "plugin_version": plugin_version,
        "shiploop_version": skill_versions["shiploop"],
        "skill_count": len(skill_versions),
        "skill_versions": skill_versions,
    }


def resolve_bin(host: str, env: dict[str, str]) -> str | None:
    env_keys = {
        "claude": "CLAUDE_BIN",
        "codex": "CODEX_BIN",
        "antigravity": "AGY_BIN",
        "grok": "GROK_BIN",
    }
    default_names = {
        "claude": "claude",
        "codex": "codex",
        "antigravity": "agy",
        "grok": "grok",
    }
    override = env.get(env_keys[host], "").strip()
    if override:
        return override if (os.path.isfile(override) and os.access(override, os.X_OK)) else shutil.which(override, path=env.get("PATH"))
    return shutil.which(default_names[host], path=env.get("PATH"))


def read_process_lines(env: dict[str, str]) -> list[tuple[int, str]]:
    ps_file = env.get("RELEASE_REFRESH_PS_FILE", "").strip()
    if ps_file:
        raw = Path(ps_file).read_text(encoding="utf-8")
    else:
        done = subprocess.run(
            ["ps", "-ax", "-ww", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        raw = done.stdout
    rows: list[tuple[int, str]] = []
    self_pid = os.getpid()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid == self_pid:
            continue
        rows.append((pid, parts[1]))
    return rows


def live_processes_under(prefixes: list[Path], env: dict[str, str]) -> list[dict]:
    """Return live processes whose command references any resolved prefix directory."""
    candidates: set[str] = set()
    for prefix in prefixes:
        candidates.add(str(prefix))
        try:
            candidates.add(str(prefix.resolve()))
        except OSError:
            pass
    # Match prefix followed by '/', whitespace, quote, or end-of-line so sibling
    # paths such as `/foo/skill-craft-other` do not false-match `/foo/skill-craft`,
    # unless wildcard_prefix is explicitly used via parent directory checks.
    patterns = [
        re.compile(r"(?<![\w/.-])" + re.escape(cand.rstrip("/")) + r"(?:/|[\s\"']|$)")
        for cand in sorted(candidates)
        if cand
    ]
    hits: list[dict] = []
    for pid, command in read_process_lines(env):
        if any(pat.search(command) for pat in patterns):
            hits.append({"pid": pid, "command": command[:240]})
    return hits


def live_grok_processes(grok_dir: Path, env: dict[str, str]) -> list[dict]:
    installed_dir = grok_dir / "installed-plugins"
    cands = {str(installed_dir)}
    try:
        cands.add(str(installed_dir.resolve()))
    except OSError:
        pass
    patterns = [
        re.compile(r"(?<![\w/.-])" + re.escape(base.rstrip("/")) + r"/skill-craft(?:-[A-Za-z0-9._-]+)?(?:/|[\s\"']|$)")
        for base in sorted(cands)
    ]
    hits: list[dict] = []
    for pid, command in read_process_lines(env):
        if any(pat.search(command) for pat in patterns):
            hits.append({"pid": pid, "command": command[:240]})
    return hits


def run_cmd(argv: list[str], *, env: dict[str, str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        done = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RefreshError(f"command timed out after {timeout}s: {' '.join(argv)}") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()
        raise RefreshError(f"command failed ({done.returncode}): {' '.join(argv)}\n{detail}")
    return done


def verify_installed_tree(package_dir: Path, expected: dict) -> dict:
    """Verify bundled skill leaves and versions inside an installed plugin directory."""
    skills_dir = package_dir / "skills"
    if not skills_dir.is_dir():
        return {
            "ok": False,
            "path": str(package_dir),
            "error": f"missing skills/ directory in {package_dir}",
        }
    found_versions: dict[str, str | None] = {}
    for entry in sorted(skills_dir.iterdir()):
        card = entry / "SKILL.md"
        if entry.is_dir() and card.is_file():
            found_versions[entry.name] = card_version(card)
    expected_versions: dict[str, str] = expected["skill_versions"]
    missing = sorted(set(expected_versions) - set(found_versions))
    extra = sorted(set(found_versions) - set(expected_versions))
    mismatched = {
        leaf: {"expected": expected_versions[leaf], "installed": found_versions[leaf]}
        for leaf in sorted(set(expected_versions) & set(found_versions))
        if found_versions[leaf] != expected_versions[leaf]
    }
    shiploop_installed = found_versions.get("shiploop")
    ok = not missing and not extra and not mismatched and shiploop_installed == expected["shiploop_version"]
    result: dict = {
        "ok": ok,
        "path": str(package_dir),
        "skill_count": len(found_versions),
        "shiploop_version": shiploop_installed,
    }
    if missing:
        result["missing_skills"] = missing
    if extra:
        result["extra_skills"] = extra
    if mismatched:
        result["version_mismatches"] = mismatched
    return result


def home_dir(env: dict[str, str]) -> Path:
    return Path(env.get("HOME") or str(Path.home()))


def claude_config_dir(env: dict[str, str]) -> Path:
    return Path(env.get("CLAUDE_CONFIG_DIR") or str(home_dir(env) / ".claude"))


def codex_home_dir(env: dict[str, str]) -> Path:
    return Path(env.get("CODEX_HOME") or str(home_dir(env) / ".codex"))


def antigravity_plugins_dir(env: dict[str, str]) -> Path:
    return Path(env.get("ANTIGRAVITY_PLUGINS_DIR") or str(home_dir(env) / ".gemini" / "config" / "plugins"))


def grok_config_dir(env: dict[str, str]) -> Path:
    return Path(env.get("GROK_CONFIG_DIR") or str(home_dir(env) / ".grok"))


def cursor_config_dir(env: dict[str, str]) -> Path:
    return Path(env.get("CURSOR_CONFIG_DIR") or str(home_dir(env) / ".cursor"))


def readback_claude(binary: str, marketplace: str, expected: dict, env: dict[str, str], timeout: float) -> dict:
    plugin_id = f"{PLUGIN_NAME}@{marketplace}"
    done = run_cmd([binary, "plugin", "list", "--json"], env=env, timeout=timeout)
    try:
        parsed = json.loads(done.stdout)
    except ValueError as exc:
        raise RefreshError(f"claude plugin list --json returned invalid JSON: {exc}") from exc
    rows = parsed.get("plugins", []) if isinstance(parsed, dict) else parsed
    if not isinstance(rows, list):
        raise RefreshError("claude plugin list --json returned unexpected shape")
    matches = [r for r in rows if isinstance(r, dict) and r.get("id") == plugin_id]
    if len(matches) != 1:
        return {"status": "failed", "error": f"expected 1 {plugin_id} entry in claude plugin list, found {len(matches)}"}
    row = matches[0]
    version = row.get("version")
    enabled = bool(row.get("enabled"))
    install_path = Path(row["installPath"]) if isinstance(row.get("installPath"), str) and row["installPath"] else (
        claude_config_dir(env) / "plugins" / "cache" / marketplace / PLUGIN_NAME / str(version or "")
    )
    tree = verify_installed_tree(install_path, expected)
    ok = enabled and version == expected["plugin_version"] and tree["ok"]
    out = {
        "status": "ok" if ok else "failed",
        "plugin_id": plugin_id,
        "enabled": enabled,
        "version": version,
        "shiploop_version": tree.get("shiploop_version"),
        "skill_count": tree.get("skill_count"),
        "tree": tree,
        "note": "Restart open Claude Code sessions to load updated plugin hooks and skills.",
    }
    if not ok and "error" not in out:
        if not enabled:
            out["error"] = f"{plugin_id} is disabled in Claude Code"
        elif version != expected["plugin_version"]:
            out["error"] = f"Claude Code has {plugin_id} {version!r}, expected {expected['plugin_version']!r}"
        else:
            out["error"] = "Claude Code installed skill tree does not match release"
    return out


def readback_codex(binary: str, marketplace: str, expected: dict, env: dict[str, str], timeout: float) -> dict:
    plugin_id = f"{PLUGIN_NAME}@{marketplace}"
    done = run_cmd([binary, "plugin", "list", "--marketplace", marketplace, "--json"], env=env, timeout=timeout)
    try:
        parsed = json.loads(done.stdout)
    except ValueError as exc:
        raise RefreshError(f"codex plugin list --json returned invalid JSON: {exc}") from exc
    installed_rows = parsed.get("installed", []) if isinstance(parsed, dict) else []
    matches = [
        r for r in installed_rows
        if isinstance(r, dict) and (r.get("pluginId") == plugin_id or r.get("name") == PLUGIN_NAME)
    ]
    if len(matches) != 1:
        return {"status": "failed", "error": f"expected 1 {plugin_id} entry in codex plugin list, found {len(matches)}"}
    row = matches[0]
    version = row.get("version")
    enabled = bool(row.get("installed")) and bool(row.get("enabled", True))
    candidates: list[Path] = []
    cache_path = codex_home_dir(env) / "plugins" / "cache" / marketplace / PLUGIN_NAME / str(version or "")
    if cache_path.is_dir():
        candidates.append(cache_path)
    src = row.get("source")
    if isinstance(src, dict) and isinstance(src.get("path"), str) and Path(src["path"]).is_dir():
        src_path = Path(src["path"])
        if src_path not in candidates:
            candidates.append(src_path)
    if not candidates:
        candidates.append(cache_path)
    trees = [verify_installed_tree(p, expected) for p in candidates]
    trees_ok = all(t["ok"] for t in trees)
    ok = enabled and version == expected["plugin_version"] and trees_ok
    primary = trees[0]
    out = {
        "status": "ok" if ok else "failed",
        "plugin_id": plugin_id,
        "enabled": enabled,
        "version": version,
        "shiploop_version": primary.get("shiploop_version"),
        "skill_count": primary.get("skill_count"),
        "trees": trees,
        "note": "Start a new Codex thread/task to pick up the refreshed plugin.",
    }
    if not ok:
        if not enabled:
            out["error"] = f"{plugin_id} is not enabled in Codex"
        elif version != expected["plugin_version"]:
            out["error"] = f"Codex has {plugin_id} {version!r}, expected {expected['plugin_version']!r}"
        else:
            out["error"] = "Codex installed skill tree does not match release"
    return out


def readback_antigravity(binary: str, expected: dict, env: dict[str, str], timeout: float) -> dict:
    done = run_cmd([binary, "plugin", "list", "--json"], env=env, timeout=timeout)
    try:
        rows = json.loads(done.stdout)
    except ValueError as exc:
        raise RefreshError(f"agy plugin list --json returned invalid JSON: {exc}") from exc
    if not isinstance(rows, list):
        raise RefreshError("agy plugin list --json returned unexpected shape")
    matches = [r for r in rows if isinstance(r, dict) and r.get("name") == PLUGIN_NAME]
    if len(matches) != 1:
        return {
            "status": "failed",
            "error": f"expected 1 {PLUGIN_NAME} entry in agy plugin list, found {len(matches)}",
        }
    row = matches[0]
    version = row.get("version")
    enabled = bool(row.get("enabled"))
    install_path = Path(row["path"]) if isinstance(row.get("path"), str) and row["path"] else (
        antigravity_plugins_dir(env) / PLUGIN_NAME
    )
    listed_skills = sorted(row.get("skills") or [])
    listed_hooks = sorted(row.get("hooks") or [])
    tree = verify_installed_tree(install_path, expected)
    hooks_ok = "shiploop" in listed_hooks and (install_path / "hooks.json").is_file()
    skills_listed_ok = listed_skills == sorted(expected["skill_versions"])
    ok = enabled and version == expected["plugin_version"] and tree["ok"] and hooks_ok and skills_listed_ok
    out = {
        "status": "ok" if ok else "failed",
        "name": PLUGIN_NAME,
        "enabled": enabled,
        "version": version,
        "shiploop_version": tree.get("shiploop_version"),
        "skill_count": tree.get("skill_count"),
        "hooks": listed_hooks,
        "tree": tree,
        "note": "Antigravity App and agy CLI share ~/.gemini/config/plugins/skill-craft live.",
    }
    if not ok:
        if not enabled:
            out["error"] = f"{PLUGIN_NAME} is disabled in Antigravity"
        elif version != expected["plugin_version"]:
            out["error"] = f"Antigravity has {PLUGIN_NAME} {version!r}, expected {expected['plugin_version']!r}"
        elif not hooks_ok:
            out["error"] = "Antigravity plugin is missing root hooks.json or shiploop hook registration"
        elif not skills_listed_ok:
            out["error"] = "Antigravity discovered skill list differs from expected release skills"
        else:
            out["error"] = "Antigravity installed skill tree does not match release"
    return out


def readback_grok(binary: str, marketplace: str, expected: dict, env: dict[str, str], timeout: float) -> dict:
    done = run_cmd([binary, "plugin", "list", "--json"], env=env, timeout=timeout)
    try:
        rows = json.loads(done.stdout)
    except ValueError as exc:
        raise RefreshError(f"grok plugin list --json returned invalid JSON: {exc}") from exc
    if not isinstance(rows, list):
        raise RefreshError("grok plugin list --json returned unexpected shape")
    matches = [r for r in rows if isinstance(r, dict) and r.get("name") == PLUGIN_NAME]
    if len(matches) != 1:
        return {"status": "failed", "error": f"expected 1 {PLUGIN_NAME} entry in grok plugin list, found {len(matches)}"}
    row = matches[0]
    version = row.get("version")
    enabled = row.get("status", "installed") == "installed" and row.get("enabled", True) is not False
    install_path = Path(row["path"]) if isinstance(row.get("path"), str) and row["path"] else (
        grok_config_dir(env) / "installed-plugins" / PLUGIN_NAME
    )
    tree = verify_installed_tree(install_path, expected)
    ok = enabled and version == expected["plugin_version"] and tree["ok"]
    out = {
        "status": "ok" if ok else "failed",
        "name": PLUGIN_NAME,
        "marketplace": row.get("marketplace") or marketplace,
        "enabled": enabled,
        "version": version,
        "shiploop_version": tree.get("shiploop_version"),
        "skill_count": tree.get("skill_count"),
        "tree": tree,
        "note": "Start a new Grok session so its leader loads updated plugin hooks.",
    }
    if not ok:
        if not enabled:
            out["error"] = f"{PLUGIN_NAME} is not installed/enabled in Grok"
        elif version != expected["plugin_version"]:
            out["error"] = f"Grok has {PLUGIN_NAME} {version!r}, expected {expected['plugin_version']!r}"
        else:
            out["error"] = "Grok installed skill tree does not match release"
    return out


def readback_cursor(marketplace: str, expected: dict, env: dict[str, str]) -> dict:
    plugin_id = f"{PLUGIN_NAME}@{marketplace}"
    local_shadow = cursor_config_dir(env) / "plugins" / "local" / PLUGIN_NAME
    if local_shadow.exists() or local_shadow.is_symlink():
        return {
            "status": "failed",
            "mode": "shadowed",
            "error": (
                f"local Cursor plugin copy at {local_shadow} shadows Claude Code's Imported copy; "
                "move or remove it so skills do not load twice or lag releases"
            ),
        }
    inventory_path = claude_config_dir(env) / "plugins" / "installed_plugins.json"
    if not inventory_path.is_file():
        return {
            "status": "unavailable",
            "mode": "no-claude-inventory",
            "note": f"{inventory_path} not present; Cursor imports Claude Code's {plugin_id} on machines with Claude Code.",
        }
    try:
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "failed", "error": f"unreadable {inventory_path}: {exc}"}
    records = (data.get("plugins") or {}).get(plugin_id) if isinstance(data, dict) else None
    if not isinstance(records, list) or not records or not isinstance(records[0], dict):
        return {
            "status": "failed",
            "error": f"{plugin_id} is absent from {inventory_path}; update Claude Code so Cursor imports it",
        }
    rec = records[0]
    version = rec.get("version")
    install_path = Path(rec["installPath"]) if isinstance(rec.get("installPath"), str) and rec["installPath"] else (
        claude_config_dir(env) / "plugins" / "cache" / marketplace / PLUGIN_NAME / str(version or "")
    )
    tree = verify_installed_tree(install_path, expected)
    ok = version == expected["plugin_version"] and tree["ok"]
    out = {
        "status": "ok" if ok else "failed",
        "mode": "imported-from-claude",
        "plugin_id": plugin_id,
        "version": version,
        "shiploop_version": tree.get("shiploop_version"),
        "skill_count": tree.get("skill_count"),
        "tree": tree,
        "note": "Relaunch Cursor after a Claude Code plugin update so Cursor reloads the Imported plugin.",
    }
    if not ok:
        if version != expected["plugin_version"]:
            out["error"] = (
                f"Claude Code's installed_plugins.json (imported by Cursor) has {plugin_id} {version!r}, "
                f"expected {expected['plugin_version']!r}"
            )
        else:
            out["error"] = "Claude Code cache imported by Cursor does not match release skill tree"
    return out


def selected_hosts(raw_hosts: list[str] | None) -> tuple[list[str], bool]:
    if not raw_hosts or "all" in raw_hosts:
        return list(ALL_HOSTS), False
    ordered: list[str] = []
    for item in raw_hosts:
        if item not in ordered:
            ordered.append(item)
    return ordered, True


def refresh_host(
    host: str,
    *,
    explicit: bool,
    expected: dict,
    marketplace: str,
    antigravity_source: str,
    check_only: bool,
    dry_run: bool,
    allow_live: bool,
    env: dict[str, str],
    timeout: float,
) -> dict:
    if host == "cursor":
        if dry_run and not check_only:
            local_shadow = cursor_config_dir(env) / "plugins" / "local" / PLUGIN_NAME
            if local_shadow.exists() or local_shadow.is_symlink():
                return {
                    "status": "blocked",
                    "error": f"local Cursor plugin copy at {local_shadow} shadows Claude Code's Imported copy",
                }
            return {
                "status": "dry-run",
                "commands": [],
                "note": "Cursor imports Claude Code's skill-craft@whichguy copy; no separate CLI command runs.",
            }
        return readback_cursor(marketplace, expected, env)

    binary = resolve_bin(host, env)
    if not binary:
        required = explicit or host in REQUIRED_ALL_HOSTS
        return {
            "status": "failed" if required else "unavailable",
            "error": f"{host} CLI binary not found on PATH" if required else None,
        }

    plugin_id = f"{PLUGIN_NAME}@{marketplace}"
    commands: list[list[str]]
    live_hits: list[dict] = []
    if host == "claude":
        commands = [
            [binary, "plugin", "marketplace", "update", marketplace],
            [binary, "plugin", "update", plugin_id, "--scope", "user"],
        ]
    elif host == "codex":
        live_hits = live_processes_under(
            [
                codex_home_dir(env) / "plugins" / "cache" / marketplace / PLUGIN_NAME,
                codex_home_dir(env) / ".tmp" / "marketplaces" / marketplace / "plugins" / PLUGIN_NAME,
            ],
            env,
        )
        commands = [[binary, "plugin", "marketplace", "upgrade", marketplace]]
    elif host == "antigravity":
        live_hits = live_processes_under([antigravity_plugins_dir(env) / PLUGIN_NAME], env)
        commands = [[binary, "plugin", "install", antigravity_source]]
    elif host == "grok":
        live_hits = live_grok_processes(grok_config_dir(env), env)
        commands = [
            [binary, "plugin", "marketplace", "update", marketplace],
            [binary, "plugin", "update", PLUGIN_NAME],
        ]
    else:
        raise RefreshError(f"unsupported host {host!r}")

    if check_only:
        if host == "claude":
            result = readback_claude(binary, marketplace, expected, env, timeout)
        elif host == "codex":
            result = readback_codex(binary, marketplace, expected, env, timeout)
        elif host == "antigravity":
            result = readback_antigravity(binary, expected, env, timeout)
        else:
            result = readback_grok(binary, marketplace, expected, env, timeout)
        if live_hits:
            result["live_processes"] = live_hits
        return result

    if live_hits and not allow_live:
        return {
            "status": "blocked",
            "error": (
                f"refusing to refresh {host} while {len(live_hits)} live process(es) execute from its installed "
                f"{PLUGIN_NAME} directory (wait for the run to finish or pass --allow-live)"
            ),
            "live_processes": live_hits,
        }

    if dry_run:
        out = {"status": "dry-run", "commands": commands}
        if live_hits:
            out["live_processes"] = live_hits
        return out

    for cmd in commands:
        run_cmd(cmd, env=env, timeout=timeout)

    if host == "claude":
        result = readback_claude(binary, marketplace, expected, env, timeout)
    elif host == "codex":
        result = readback_codex(binary, marketplace, expected, env, timeout)
    elif host == "antigravity":
        result = readback_antigravity(binary, expected, env, timeout)
    else:
        result = readback_grok(binary, marketplace, expected, env, timeout)
    result["commands_run"] = commands
    if live_hits:
        result["live_processes"] = live_hits
    return result


def main(argv: list[str] | None = None) -> int:
    default_repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=default_repo, help="skill-craft checkout root")
    parser.add_argument(
        "--host",
        action="append",
        choices=(*ALL_HOSTS, "all"),
        help="target host (repeatable; default: all)",
    )
    parser.add_argument("--marketplace", default=DEFAULT_MARKETPLACE, help="marketplace catalog name (default: whichguy)")
    parser.add_argument(
        "--antigravity-source",
        default=DEFAULT_ANTIGRAVITY_SOURCE,
        help="GitHub subfolder URL or local plugin path passed to `agy plugin install`",
    )
    parser.add_argument("--check-only", action="store_true", help="verify installed host versions and skills without updating")
    parser.add_argument("--dry-run", action="store_true", help="validate preconditions and print planned commands only")
    parser.add_argument("--allow-live", action="store_true", help="allow refreshing Codex/Antigravity/Grok despite live runs")
    parser.add_argument(
        "--allow-unreleased",
        action="store_true",
        help="allow running when the checkout has pending change notes or unsynced views",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="per-command timeout in seconds (default: 300)")
    args = parser.parse_args(argv)

    if args.check_only and args.dry_run:
        print(json.dumps({"status": "blocked", "error": "--check-only and --dry-run are mutually exclusive"}, sort_keys=True),
              file=sys.stderr)
        return 1
    if args.timeout <= 0:
        print(json.dumps({"status": "blocked", "error": "--timeout must be positive"}, sort_keys=True), file=sys.stderr)
        return 1

    env = dict(os.environ)
    try:
        expected = expected_release(args.repo, allow_unreleased=args.allow_unreleased)
        hosts, explicit = selected_hosts(args.host)
        results: dict[str, dict] = {}
        failed = False
        for name in hosts:
            try:
                host_result = refresh_host(
                    name,
                    explicit=explicit,
                    expected=expected,
                    marketplace=args.marketplace,
                    antigravity_source=args.antigravity_source,
                    check_only=args.check_only,
                    dry_run=args.dry_run,
                    allow_live=args.allow_live,
                    env=env,
                    timeout=args.timeout,
                )
            except RefreshError as exc:
                host_result = {"status": "failed", "error": str(exc)}
            results[name] = host_result
            if host_result.get("status") in {"failed", "blocked"}:
                failed = True

        overall = (
            "blocked"
            if failed
            else ("dry-run" if args.dry_run else ("verified" if args.check_only else "refreshed"))
        )
        summary = {
            "status": overall,
            "expected": {
                "plugin": PLUGIN_NAME,
                "plugin_version": expected["plugin_version"],
                "shiploop_version": expected["shiploop_version"],
                "skill_count": expected["skill_count"],
                "skills": sorted(expected["skill_versions"]),
            },
            "hosts": results,
        }
        stream = sys.stderr if failed else sys.stdout
        print(json.dumps(summary, indent=2, sort_keys=True), file=stream)
        return 1 if failed else 0
    except (RefreshError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
