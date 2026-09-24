#!/usr/bin/env python3
"""Opt-in real CLI install smoke in disposable profiles (no model/API calls).

Tests a build of the current local source, not the committed plugins/ tree
or its published Git catalog pins.
Run with --host claude|grok|codex. The personal host profiles are never used.
--bundle NAME installs one multi-skill bundle view (plugins/NAME) and checks
that every declared member card is materialized once with identical bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import package_build

ROOT = Path(__file__).resolve().parents[1]
LEAVES = ("skill-interop", "review-coverage")
ASK_AGENT = "ask-agent"
GIT_CONTEXT_ENVIRONMENT = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM", "GIT_NAMESPACE",
})


def isolated_environment(parent: dict[str, str], home: Path) -> dict[str, str]:
    """Allow only process essentials; no ambient provider or config credentials."""
    allowed = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR", "DEVELOPER_DIR",
               "SYSTEMROOT", "WINDIR", "PATHEXT")
    env = {key: parent[key] for key in allowed if key in parent}
    env.update(HOME=str(home), CODEX_HOME=str(home / ".codex"),
               CLAUDE_CONFIG_DIR=str(home / ".claude"),
               XDG_CONFIG_HOME=str(home / ".config"), XDG_DATA_HOME=str(home / ".local/share"),
               XDG_CACHE_HOME=str(home / ".cache"), XDG_STATE_HOME=str(home / ".local/state"),
               GROK_CONFIG_DIR=str(home / ".grok"),
               GROK_CLAUDE_SKILLS_ENABLED="false", GROK_CURSOR_SKILLS_ENABLED="false",
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", GIT_TERMINAL_PROMPT="0",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return env


def redact(text: str, parent: dict[str, str]) -> str:
    for key, value in parent.items():
        if re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|ACCESS_KEY|PRIVATE_KEY", key, re.I) and len(value) >= 6:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(bearer\s+)[\w.+/=-]+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})", "[REDACTED]", text)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_workspace_git_context_key(key: str) -> bool:
    return key in GIT_CONTEXT_ENVIRONMENT or key.startswith("GIT_CONFIG_")


def workspace_helper_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Retain the disposable profile while removing helper-rejected Git state."""
    result = {
        key: value
        for key, value in environment.items()
        if not _is_workspace_git_context_key(key)
    }
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def environment_summary(environment: Mapping[str, str]) -> dict[str, Any]:
    """Record only safe environment-shape evidence for a command receipt."""
    credential_keys = sorted(
        key for key in environment
        if re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|ACCESS_KEY|PRIVATE_KEY", key, re.I)
    )
    return {
        "HOME": environment.get("HOME"),
        "CODEX_HOME": environment.get("CODEX_HOME"),
        "keys": sorted(environment),
        "git_context_overrides": sorted(key for key in environment if _is_workspace_git_context_key(key)),
        "credential_keys": credential_keys,
    }


def package_tree_digests(root: Path) -> dict[str, str]:
    """Digest one installed skill tree, excluding Python bytecode on both sides."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise RuntimeError(f"package tree contains a symlink: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"package tree contains a non-regular entry: {relative}")
        result[relative.as_posix()] = digest(path)
    if not result:
        raise RuntimeError(f"package tree is empty: {root}")
    return result


def installed_skill_card(home: Path, host: str, name: str) -> Path:
    """Return one materialized cache card confined to the disposable profile."""
    installed_root = home / {
        "grok": ".grok/installed-plugins",
        "claude": ".claude/plugins/cache",
        "codex": ".codex/plugins/cache",
    }[host]
    matches = [
        path for path in installed_root.rglob("SKILL.md")
        if path.parent.name == name and not path.is_symlink()
    ]
    if len(matches) != 1:
        observed = [str(path.relative_to(home)) for path in home.rglob("SKILL.md")]
        raise RuntimeError(
            f"expected one installed cache copy of {name}, got {matches}; "
            f"observed skills: {observed}"
        )
    actual = matches[0]
    relative = actual.relative_to(home)
    current = home
    for part in (".", *relative.parts):
        if part != ".":
            current = current / part
        if current.is_symlink():
            raise RuntimeError(f"installed cache path contains a symlink: {current}")
    actual.resolve().relative_to(home.resolve())
    return actual


def frontmatter_version(card: Path) -> str:
    match = re.search(r"(?m)^version:\s*([^\s#]+)\s*$", card.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"installed skill card has no frontmatter version: {card}")
    return match.group(1)


def run_smoke(host: str, binary: str) -> dict:
    resolved = shutil.which(binary)
    if not resolved:
        raise RuntimeError(f"{host} CLI unavailable: {binary}")
    receipts = []
    with tempfile.TemporaryDirectory(prefix=f"skill-craft-{host}-consumer-") as temporary:
        scratch = Path(temporary)
        home = scratch / "consumer home"
        project = scratch / "unrelated project"
        market = scratch / "local marketplace"
        for directory in (home, project, market):
            directory.mkdir()
        parent = dict(os.environ)
        # Child-process host configuration only. Never change the running shell's
        # home, authenticate, or copy personal configuration/credentials here.
        env = isolated_environment(parent, home)
        env.update({f"{host.upper()}_BIN": resolved})
        for path in (home / ".codex", home / ".claude", home / ".grok"):
            path.mkdir()
        plugins = []
        for name in LEAVES:
            source = package_build.plugins() / name
            shutil.copytree(source, market / "plugins" / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            if host == "grok":
                plugins.append({"name": name, "source": {"type": "local", "path": f"./plugins/{name}"}})
            elif host == "codex":
                plugins.append({"name": name, "source": {"source": "local", "path": f"./plugins/{name}"},
                                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                                "category": "Productivity"})
            else:
                plugins.append({"name": name, "source": f"./plugins/{name}"})
        catalog_name = "skill-craft-consumer-smoke"
        catalog = {"name": catalog_name, "plugins": plugins}
        if host == "claude":
            catalog["owner"] = {"name": "Skill Craft local test"}
        manifest_dir = market / ({"grok": ".grok-plugin", "claude": ".claude-plugin", "codex": ".agents/plugins"}[host])
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "marketplace.json").write_text(json.dumps(catalog), encoding="utf-8")

        def call(argv):
            result = subprocess.run(argv, cwd=project, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            receipts.append({"argv": argv, "exit": result.returncode,
                             "stdout": redact(result.stdout, parent), "stderr": redact(result.stderr, parent)})
            if result.returncode:
                raise RuntimeError(redact(f"command failed ({result.returncode}): {argv}\n{result.stdout}\n{result.stderr}", parent))
            return result.stdout

        def installed_skill(name):
            # Only accept materialized plugin files inside this disposable home.
            # A file in the source marketplace is not installation evidence.
            actual = installed_skill_card(home, host, name)
            expected = market / "plugins" / name / "skills" / name / "SKILL.md"
            if digest(actual) != digest(expected):
                raise RuntimeError(f"installed skill body mismatch: {name}")
            return actual

        version = call([resolved, "--version"]).strip()
        # Bootstrap the helper itself via the real host CLI; subsequent catalog
        # and plugin operations deliberately go through the installed helper.
        call([resolved, "plugin", "marketplace", "add", str(market)])
        helper_id = "skill-interop" if host == "grok" else f"skill-interop@{catalog_name}"
        install = [resolved, "plugin", "add" if host == "codex" else "install", helper_id]
        if host == "grok":
            install.append("--trust")
        call(install)
        helper = installed_skill("skill-interop").parent / "scripts/marketplace-run.sh"
        wrapper = ["bash", str(helper), "--host", host]
        call(wrapper + ["marketplaces", "list", "--json"])
        # Register a second catalog through the installed wrapper to exercise its
        # add route without duplicate-registration behavior hiding a defect.
        second = scratch / "second marketplace"
        shutil.copytree(market, second)
        second_catalog = second / manifest_dir.relative_to(market) / "marketplace.json"
        second_data = json.loads(second_catalog.read_text())
        second_data["name"] = "skill-craft-consumer-second"
        second_catalog.write_text(json.dumps(second_data))
        call(wrapper + ["marketplaces", "add", str(second)])
        # Grok qualifies local markets by normalized directory name, not the
        # catalog's display name. Do not let the second registration make the
        # intentionally duplicated plugin name ambiguous.
        target_id = "review-coverage@local/local-marketplace" if host == "grok" else f"review-coverage@{catalog_name}"
        call(wrapper + ["plugins", "install", target_id] + (["--trust"] if host == "grok" else []))
        listed = call(wrapper + ["plugins", "list", "--json"])
        if "review-coverage" not in listed:
            raise RuntimeError("installed wrapper did not list the installed target")
        card = installed_skill("review-coverage")
        cli = card.parent / "scripts/review-coverage"
        expected_cli = market / "plugins/review-coverage/skills/review-coverage/scripts/review-coverage"
        if digest(cli) != digest(expected_cli):
            raise RuntimeError("installed bundled script mismatch")
        output = call(["python3", str(cli), "template", "--short"])
        if "Review Coverage" not in output:
            raise RuntimeError("installed template helper did not return the expected artifact")
        before_remove = {"card_sha256": digest(card), "script_sha256": digest(cli)}
        # Grok's installed identity is the name, not its catalog source selector.
        remove_id = "review-coverage" if host == "grok" else target_id
        call(wrapper + ["plugins", "uninstall", remove_id])
        listed = call(wrapper + ["plugins", "list", "--json"])
        if "review-coverage" in listed:
            raise RuntimeError("removed target remains in installed inventory")
        return {"host": host, "version": version, "status": "passed",
                "scope": "local catalog install, installed wrapper operations and script execution; no model workflow or published-pin proof",
                **before_remove, "commands": receipts}


def run_ask_agent_consumer(
    host: str,
    binary: str,
    *,
    extra_environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Exercise an installed Ask Agent package without launching a model.

    This is intentionally a local-catalog consumer probe.  It proves the
    materialized package and its managed-worktree boundary, not a published
    marketplace pin or native task delivery.
    """
    if host != "codex":
        raise RuntimeError("the Ask Agent consumer probe currently supports codex only")
    resolved = shutil.which(binary)
    if not resolved:
        raise RuntimeError(f"{host} CLI unavailable: {binary}")
    source_package = package_build.plugins() / ASK_AGENT
    source_skill = source_package / "skills" / ASK_AGENT
    if not source_skill.is_dir():
        raise RuntimeError(f"Ask Agent package is unavailable: {source_skill}")
    receipts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="skill-craft-codex-ask-agent-consumer-") as temporary:
        scratch = Path(temporary)
        home = scratch / "consumer home"
        project = scratch / "unrelated project"
        market = scratch / "local marketplace"
        for directory in (home, project, market):
            directory.mkdir()
        parent = dict(os.environ)
        env = isolated_environment(parent, home)
        env["CODEX_BIN"] = resolved
        if extra_environment:
            env.update({str(key): str(value) for key, value in extra_environment.items()})
        helper_env = workspace_helper_environment(env)
        helper_environment = environment_summary(helper_env)
        if helper_environment["git_context_overrides"]:
            raise RuntimeError("helper environment retained Git context overrides")
        if helper_environment["credential_keys"]:
            raise RuntimeError("helper environment retained credential-shaped variables")
        (home / ".codex").mkdir()

        def call(
            argv: list[str | Path],
            *,
            cwd: Path = project,
            environment: Mapping[str, str] = env,
        ) -> str:
            rendered = [str(value) for value in argv]
            result = subprocess.run(
                rendered,
                cwd=cwd,
                env=dict(environment),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
            )
            receipts.append({
                "argv": rendered,
                "cwd": str(cwd),
                "exit": result.returncode,
                "environment": environment_summary(environment),
                "stdout": redact(result.stdout, parent),
                "stderr": redact(result.stderr, parent),
            })
            if result.returncode:
                raise RuntimeError(
                    redact(
                        f"command failed ({result.returncode}): {rendered}\n"
                        f"{result.stdout}\n{result.stderr}",
                        parent,
                    )
                )
            return result.stdout

        def git(*arguments: str, cwd: Path) -> str:
            return call(["git", *arguments], cwd=cwd, environment=helper_env)

        copied_package = market / "plugins" / ASK_AGENT
        shutil.copytree(
            source_package,
            copied_package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        expected_card = copied_package / "skills" / ASK_AGENT / "SKILL.md"
        expected_tree = package_tree_digests(copied_package)
        catalog_name = "skill-craft-ask-agent-consumer"
        manifest = market / ".agents/plugins"
        manifest.mkdir(parents=True)
        catalog = {
            "name": catalog_name,
            "plugins": [{
                "name": ASK_AGENT,
                "source": {"source": "local", "path": f"./plugins/{ASK_AGENT}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }],
        }
        (manifest / "marketplace.json").write_text(json.dumps(catalog), encoding="utf-8")

        version = call([resolved, "--version"]).strip()
        call([resolved, "plugin", "marketplace", "add", market])
        plugin_id = f"{ASK_AGENT}@{catalog_name}"
        call([resolved, "plugin", "add", plugin_id, "--json"])
        card = installed_skill_card(home, host, ASK_AGENT)
        actual_package = card.parent.parent.parent
        if card != actual_package / "skills" / ASK_AGENT / "SKILL.md":
            raise RuntimeError("installed Ask Agent card is outside its package skill tree")
        actual_tree = package_tree_digests(actual_package)
        if actual_tree != expected_tree:
            raise RuntimeError("installed Ask Agent package tree differs from the local package")
        helper = card.parent / "scripts" / "ask_agent_workspace.py"
        if helper.is_symlink() or not helper.is_file():
            raise RuntimeError("installed Ask Agent workspace helper is not a regular file")
        identity = json.loads(call(
            [sys.executable, "-B", helper, "identity", "--skill-card", card],
            environment=helper_env,
        ))
        expected_identity = {
            "status": "verified",
            "schema": "ask-agent.skill.identity.v1",
            "skill_card": str(card),
            "resolved_skill_card": str(card.resolve()),
            "resolved_helper": str(helper.resolve()),
            "version": frontmatter_version(card),
            "skill_card_sha256": digest(card),
            "helper_sha256": digest(helper),
        }
        for key, value in expected_identity.items():
            if identity.get(key) != value:
                raise RuntimeError(f"installed Ask Agent identity mismatch for {key}")

        repository = scratch / "caller repository"
        caller = scratch / "dirty caller"
        repository.mkdir()
        git("init", "-q", "-b", "main", cwd=repository)
        git("config", "user.name", "Ask Agent consumer fixture", cwd=repository)
        git("config", "user.email", "ask-agent-consumer@example.invalid", cwd=repository)
        (repository / "app.txt").write_text("base\n", encoding="utf-8")
        git("add", "app.txt", cwd=repository)
        git("commit", "-qm", "baseline", cwd=repository)
        git("worktree", "add", "-q", "-b", "consumer-fixture", str(caller), "HEAD", cwd=repository)
        if not (caller / ".git").is_file():
            raise RuntimeError("consumer caller is not a linked Git worktree")
        (caller / "app.txt").write_text("base\nstaged caller\n", encoding="utf-8")
        git("add", "app.txt", cwd=caller)
        (caller / "app.txt").write_text("base\nstaged caller\nunstaged caller\n", encoding="utf-8")
        (caller / "note.txt").write_text("untracked caller\n", encoding="utf-8")
        source_bytes = {
            name: (caller / name).read_bytes()
            for name in ("app.txt", "note.txt")
        }
        head = git("rev-parse", "HEAD", cwd=caller).strip()
        cached = git("diff", "--cached", "--binary", cwd=caller)
        raw_index = git("rev-parse", "--path-format=absolute", "--git-path", "index", cwd=caller).strip()
        index_path = Path(raw_index)
        if not index_path.is_absolute():
            index_path = caller / index_path
        index = index_path.read_bytes()

        prepared = json.loads(call([
            sys.executable, "-B", helper, "prepare",
            "--source", caller,
            "--store", scratch / "workspace store",
            "--label", "installed-codex-consumer",
            "--writers-quiescent",
        ], environment=helper_env))
        if prepared.get("status") != "prepared":
            raise RuntimeError("installed helper did not prepare a worker worktree")
        receipt = Path(prepared["receipt"])
        worktree = Path(prepared["worktree"])
        call([sys.executable, "-B", helper, "inspect", "--phase", "prepared", "--receipt", receipt], environment=helper_env)
        call([sys.executable, "-B", helper, "check-context", "--receipt", receipt], cwd=worktree, environment=helper_env)
        if (worktree / "app.txt").read_bytes() != source_bytes["app.txt"]:
            raise RuntimeError("prepared worktree did not inherit staged and unstaged caller bytes")
        if (worktree / "note.txt").read_bytes() != source_bytes["note.txt"]:
            raise RuntimeError("prepared worktree did not inherit caller untracked bytes")
        report = worktree / "reports" / "result.md"
        report.parent.mkdir()
        report_bytes = b"Installed Ask Agent consumer fixture passed. No model invoked.\n"
        report.write_bytes(report_bytes)
        returned = json.loads(call([
            sys.executable, "-B", helper, "inspect", "--phase", "returned",
            "--receipt", receipt,
            "--delivery-mode", "report-only",
            "--artifact", "reports/result.md",
        ], environment=helper_env))
        acceptance = {
            "schema": "ask-agent.acceptance.v1",
            "inspection_fingerprint": returned["fingerprint"],
            "decision": "report-consumed",
            "workers_stopped": True,
            "completion_reference": "synchronous installed-package fixture completed; no worker was launched",
            "acceptance_reference": "consumer fixture read the installed helper report",
            "artifacts": [{"path": "reports/result.md", "purpose": "installed helper qualification"}],
            "discard": [],
        }
        acceptance_path = scratch / "acceptance.json"
        acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")
        closed = json.loads(call([
            sys.executable, "-B", helper, "close", "--receipt", receipt,
            "--acceptance", acceptance_path,
        ], environment=helper_env))
        if closed.get("status") != "closed" or closed.get("decision") != "report-consumed" or closed.get("removed") is not True:
            raise RuntimeError("installed helper did not close the report-only worktree")
        replay = json.loads(call([
            sys.executable, "-B", helper, "close", "--receipt", receipt,
            "--acceptance", acceptance_path,
        ], environment=helper_env))
        if replay != closed:
            raise RuntimeError("installed helper close replay differed from the original close receipt")
        if worktree.exists():
            raise RuntimeError("installed helper left its closed worker worktree behind")
        archived = closed.get("archived_artifacts", [])
        if len(archived) != 1 or Path(archived[0]["archive"]).read_bytes() != report_bytes:
            raise RuntimeError("installed helper did not archive the consumed report bytes")
        if git("rev-parse", "HEAD", cwd=caller).strip() != head:
            raise RuntimeError("installed helper changed the caller HEAD")
        if git("diff", "--cached", "--binary", cwd=caller) != cached:
            raise RuntimeError("installed helper changed the caller staged diff")
        if index_path.read_bytes() != index:
            raise RuntimeError("installed helper changed the caller raw index")
        if any((caller / name).read_bytes() != value for name, value in source_bytes.items()):
            raise RuntimeError("installed helper changed caller working-file bytes")

        call([resolved, "plugin", "remove", plugin_id, "--json"])
        inventory = json.loads(call([resolved, "plugin", "list", "--json"]))
        installed = inventory.get("installed")
        if not isinstance(installed, list):
            raise RuntimeError("Codex plugin inventory did not provide an installed list")
        if any(item.get("pluginId") == plugin_id for item in installed if isinstance(item, dict)):
            raise RuntimeError("removed Ask Agent plugin remains in the installed inventory")
        return {
            "host": host,
            "version": version,
            "status": "passed",
            "scope": (
                "local catalog install and installed Ask Agent helper report-only workspace flow; "
                "no model workflow, native task delivery, or published-pin proof"
            ),
            "disposable_profile": str(home),
            "caller_is_linked_worktree": True,
            "caller_worktree_preserved": True,
            "caller_index_preserved": True,
            "close_replay_identical": True,
            "plugin_removed": True,
            "cache_retained_after_removal": card.exists(),
            "local_package": str(source_package),
            "selected_package": expected_identity,
            "package_files": actual_tree,
            "helper_environment": helper_environment,
            "commands": receipts,
        }


def run_bundle_smoke(host: str, binary: str, bundle: str) -> dict:
    """Install one bundle view locally and verify every member skill tree."""
    resolved = shutil.which(binary)
    if not resolved:
        raise RuntimeError(f"{host} CLI unavailable: {binary}")
    declaration = json.loads((ROOT / "bundles" / bundle / "bundle.json").read_text(encoding="utf-8"))
    members = [bundle, *(name for name in declaration["skills"] if name != bundle)]
    receipts = []
    with tempfile.TemporaryDirectory(prefix=f"skill-craft-{host}-bundle-") as temporary:
        scratch = Path(temporary)
        home = scratch / "consumer home"
        project = scratch / "unrelated project"
        market = scratch / "local marketplace"
        for directory in (home, project, market, home / ".codex", home / ".claude", home / ".grok"):
            directory.mkdir(parents=True)
        parent = dict(os.environ)
        env = isolated_environment(parent, home)
        shutil.copytree(package_build.plugins() / bundle, market / "plugins" / bundle,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        if host == "grok":
            entry = {"name": bundle, "source": {"type": "local", "path": f"./plugins/{bundle}"}}
        elif host == "codex":
            entry = {"name": bundle, "source": {"source": "local", "path": f"./plugins/{bundle}"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Productivity"}
        else:
            entry = {"name": bundle, "source": f"./plugins/{bundle}"}
        catalog_name = "skill-craft-bundle-smoke"
        catalog = {"name": catalog_name, "plugins": [entry]}
        if host == "claude":
            catalog["owner"] = {"name": "Skill Craft local test"}
        manifest_dir = market / ({"grok": ".grok-plugin", "claude": ".claude-plugin", "codex": ".agents/plugins"}[host])
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "marketplace.json").write_text(json.dumps(catalog), encoding="utf-8")

        def call(argv):
            result = subprocess.run(argv, cwd=project, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            receipts.append({"argv": argv, "exit": result.returncode,
                             "stdout": redact(result.stdout, parent), "stderr": redact(result.stderr, parent)})
            if result.returncode:
                raise RuntimeError(redact(f"command failed ({result.returncode}): {argv}\n{result.stdout}\n{result.stderr}", parent))
            return result.stdout

        version = call([resolved, "--version"]).strip()
        call([resolved, "plugin", "marketplace", "add", str(market)])
        plugin_id = bundle if host == "grok" else f"{bundle}@{catalog_name}"
        install = [resolved, "plugin", "add" if host == "codex" else "install", plugin_id]
        if host == "grok":
            install.append("--trust")
        call(install)
        verified = {}
        for member in members:
            card = installed_skill_card(home, host, member)
            expected = market / "plugins" / bundle / "skills" / member
            if package_tree_digests(card.parent) != package_tree_digests(expected):
                raise RuntimeError(f"installed member tree differs from the bundle view: {member}")
            verified[member] = digest(card)
        return {"host": host, "version": version, "status": "passed", "bundle": bundle,
                "members": verified,
                "scope": "local catalog install of one bundle view; every member card materialized once with identical bytes; no model workflow or published-pin proof",
                "commands": receipts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=("claude", "grok", "codex"))
    parser.add_argument("--bin", help="explicit host CLI executable")
    parser.add_argument("--ask-agent", action="store_true", help="run the installed Ask Agent consumer probe (codex only)")
    parser.add_argument("--bundle", help="install bundles/<NAME>'s plugin view and verify every member skill")
    args = parser.parse_args()
    if args.ask_agent and args.bundle:
        parser.error("--ask-agent and --bundle are exclusive")
    try:
        if args.bundle:
            receipt = run_bundle_smoke(args.host, args.bin or args.host, args.bundle)
        else:
            run = run_ask_agent_consumer if args.ask_agent else run_smoke
            receipt = run(args.host, args.bin or args.host)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"host": args.host, "status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
