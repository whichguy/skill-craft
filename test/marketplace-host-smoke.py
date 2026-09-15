#!/usr/bin/env python3
"""Opt-in real CLI install smoke in disposable profiles (no model/API calls).

Tests the current local package bytes, not their published Git catalog pins.
Run with --host claude|grok|codex. The personal host profiles are never used.
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
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LEAVES = ("skill-interop", "review-coverage")


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
            source = ROOT / "plugins" / name
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
            installed_root = home / ({"grok": ".grok/installed-plugins",
                                      "claude": ".claude/plugins/cache",
                                      "codex": ".codex/plugins/cache"}[host])
            matches = [p for p in installed_root.rglob("SKILL.md")
                       if p.parent.name == name and not p.is_symlink()]
            if len(matches) != 1:
                observed = [str(path.relative_to(home)) for path in home.rglob("SKILL.md")]
                raise RuntimeError(f"expected one installed cache copy of {name}, got {matches}; observed skills: {observed}")
            actual = matches[0]
            actual.resolve().relative_to(home.resolve())
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=("claude", "grok", "codex"))
    parser.add_argument("--bin", help="explicit host CLI executable")
    args = parser.parse_args()
    try:
        receipt = run_smoke(args.host, args.bin or args.host)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"host": args.host, "status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
