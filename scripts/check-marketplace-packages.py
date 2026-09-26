#!/usr/bin/env python3
"""Validate complete generated packages without installing or executing skills.

This is an offline payload gate, not proof of host/model execution. Host-specific
validators and installed-consumer tests remain separate release requirements.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path


NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SCRIPT_SUFFIX_INTERPRETERS = {
    ".py": "python3",
    ".sh": "bash",
    ".js": "node",
    ".cjs": "node",
    ".mjs": "node",
}
CODEX_INTERFACE_TEXT_FIELDS = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
)

# These are the current, versioned native package contracts. They deliberately
# name the helpers a loaded SKILL.md tells the host to invoke, rather than
# treating an arbitrary file under scripts/ as an entrypoint. Keep this small
# mapping in lockstep with a native package contract/release; unknown packages
# use the conservative recognized-script fallback below.
NATIVE_SCRIPT_ENTRYPOINTS: dict[str, dict[str, str]] = {
    "ask-agent": {"scripts/ask_agent_workspace.py": "python3"},
    "devloop": {"scripts/devloop-run": "bash"},
    "evidence-gates": {"scripts/evidence-gates": "python3"},
    "plan-dispatcher": {"scripts/dispatch.js": "node"},
    "improve": {"runtime/until-loop/scripts/until_loop_ephemeral.py": "python3"},
    "review-coverage": {"scripts/review-coverage": "python3"},
    "shiploop": {"scripts/shiploop": "python3"},
    "shiploop-e2e-audit": {
        "scripts/resolve_harness.py": "python3",
        "harness/run.py": "python3",
        "harness/check_suite.py": "python3",
    },
    "skill-interop": {
        "scripts/marketplace-run.sh": "bash",
        "scripts/scaffold-skill.sh": "bash",
    },
}


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    body = text[4:text.index("\n---\n", 4)]
    return {
        match[1]: match[2].strip().strip("\"'")
        for match in re.finditer(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*([^\n]*)$", body, re.M)
    }


def confined(root: Path, value: str) -> bool:
    if not value.startswith("./") or "\\" in value:
        return False
    if ".." in Path(value).parts:
        return False
    try:
        (root / value).resolve().relative_to(root.resolve())
    except (ValueError, OSError, RuntimeError):
        return False
    return True


def script_interpreter(path: Path, source: str) -> str | None:
    """Infer an invokable interpreter from a conventional suffix or shebang."""
    if path.suffix in SCRIPT_SUFFIX_INTERPRETERS:
        return SCRIPT_SUFFIX_INTERPRETERS[path.suffix]
    first_line = source.splitlines()[0] if source else ""
    if not first_line.startswith("#!"):
        return None
    command = first_line[2:].strip().split()
    if not command:
        return None
    interpreter = Path(command[0]).name
    if interpreter == "env":
        command = command[1:]
        if command[:1] == ["-S"]:
            command = command[1:]
        if not command:
            return None
        interpreter = Path(command[0]).name
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", interpreter):
        return "python3"
    if interpreter in ("bash", "sh"):
        return "bash"
    if interpreter == "node":
        return "node"
    return None


def validate_script_file(path: Path, expected: str | None) -> str | None:
    """Return one diagnostic for a declared or fallback script candidate."""
    if not path.is_file() or path.is_symlink():
        return "is missing or not a regular file"
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return f"is unreadable: {exc}"
    actual = script_interpreter(path, source)
    if actual is None:
        return "is not a recognized script (expected a supported extension or shebang)"
    if expected is not None and actual != expected:
        return f"expected {expected}, found {actual}"
    # Native inventory entries record an explicit interpreter, so their helper
    # need not be executable (for example, ``python3 scripts/helper``). An
    # unknown extensionless shebang is only accepted as a direct entrypoint,
    # which must carry an executable mode.
    if expected is None and not path.suffix and not path.stat().st_mode & 0o111:
        return "is an extensionless shebang command but is not executable"
    return None


def validate_script_entrypoints(name: str, skill_root: Path, kind: str, errors: list[str]) -> None:
    """Validate the actual bundled entrypoints for a script-backed package."""
    declared = NATIVE_SCRIPT_ENTRYPOINTS.get(name)
    if declared is not None:
        for relative, expected in declared.items():
            problem = validate_script_file(skill_root / relative, expected)
            if problem:
                errors.append(
                    f"{kind} declared entrypoint {relative} {problem}"
                )
        return

    scripts = skill_root / "scripts"
    if not scripts.is_dir():
        errors.append(f"{kind} SKILL.md has no runnable bundled script entrypoint")
        return
    for candidate in sorted(scripts.rglob("*")):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        problem = validate_script_file(candidate, None)
        if problem is None:
            return
        if problem.endswith("but is not executable"):
            relative = candidate.relative_to(skill_root).as_posix()
            errors.append(f"{kind} script candidate {relative} {problem}")
            return
    errors.append(f"{kind} SKILL.md has no runnable bundled script entrypoint")


def validate_codex_interface(codex: dict, errors: list[str]) -> None:
    interface = codex.get("interface")
    if not isinstance(interface, dict):
        errors.append("Codex interface must be an object")
        return
    for field in CODEX_INTERFACE_TEXT_FIELDS:
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Codex interface {field} must be a non-empty string")
    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities or not all(
        isinstance(value, str) and value.strip() for value in capabilities
    ):
        errors.append("Codex interface capabilities must be a non-empty string array")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or not prompts or len(prompts) > 3 or not all(
        isinstance(value, str) and value.strip() and len(value) <= 128 for value in prompts
    ):
        errors.append("Codex interface defaultPrompt must contain one to three short strings")


# Generated from skills/<leaf>/host-hooks.json: each host's file, the plugin
# root variable its commands use, and the manifest that must point at it.
HOOK_FILES = {
    "hooks.json": ("${CLAUDE_PLUGIN_ROOT}", None),
    "codex.json": ("$PLUGIN_ROOT", ".codex-plugin"),
    "cursor.json": ("${CURSOR_PLUGIN_ROOT}", ".cursor-plugin"),
}


def validate_hooks(package: Path, skills: list[str], errors: list[str]) -> None:
    """Hooks may only be the generated per-host files, each running a bundled skill's own script."""
    hook_dir = package / "hooks"
    present = sorted(item.name for item in hook_dir.iterdir()) if hook_dir.is_dir() else []
    for file_name in present:
        if file_name not in HOOK_FILES:
            errors.append(f"hooks/{file_name}: not a generated host hook file")
    for file_name, (variable, adapter) in HOOK_FILES.items():
        if adapter is not None:
            try:
                manifest = json.loads((package / adapter / "plugin.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                manifest = {}
            declared = manifest.get("hooks") if isinstance(manifest, dict) else None
            expected = f"./hooks/{file_name}" if file_name in present else None
            if declared != expected:
                errors.append(f"{adapter}/plugin.json: hooks must be {expected!r}, found {declared!r}")
        if file_name not in present:
            continue
        try:
            data = json.loads((hook_dir / file_name).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"hooks/{file_name}: unreadable or invalid JSON: {exc}")
            continue
        groups = (data.get("hooks") or {}) if isinstance(data, dict) else {}
        entries = []
        for event, items in groups.items() if isinstance(groups, dict) else ():
            for item in items if isinstance(items, list) else ():
                entries.extend(item.get("hooks", [item]) if isinstance(item, dict) else [item])
        if not entries:
            errors.append(f"hooks/{file_name}: declares no hook commands")
        pattern = re.compile(re.escape(variable) + r"/skills/([a-z0-9][a-z0-9-]*)/scripts/([^/]+)")
        for entry in entries:
            command = entry.get("command") if isinstance(entry, dict) else None
            match = pattern.fullmatch(command) if isinstance(command, str) else None
            target = package / "skills" / match[1] / "scripts" / match[2] if match else None
            if (not match or match[1] not in skills or not target.is_file()
                    or not os.access(target, os.X_OK)):
                errors.append(f"hooks/{file_name}: command must run an executable in a bundled "
                              f"skills/<skill>/scripts/ via {variable}: {command!r}")


def validate_package(package: Path) -> list[str]:
    """Return all actionable errors, including malformed/unreadable payloads."""
    errors: list[str] = []
    name = package.name
    if not package.is_dir() or package.is_symlink():
        return [f"{package}: package must be a real directory"]
    if not NAME.fullmatch(name):
        errors.append("package folder must be a normalized plugin name")

    # Reject links before opening any package payload. A generated package must
    # be self-contained, and preflight makes a symlink diagnostic deterministic
    # instead of accidentally reading through it first.
    links = sorted(
        item.relative_to(package).as_posix()
        for item in package.rglob("*")
        if item.is_symlink()
    )
    if links:
        return [f"residual symlink in payload: {relative}" for relative in links]

    for required in ("LICENSE", "README.md"):
        target = package / required
        try:
            if not target.is_file() or not target.read_text(encoding="utf-8").strip():
                errors.append(f"missing or empty {required}")
        except (OSError, UnicodeError) as exc:
            errors.append(f"unreadable {required}: {exc}")

    manifests: dict[str, dict] = {}
    for adapter in (".claude-plugin", ".codex-plugin"):
        relative = f"{adapter}/plugin.json"
        try:
            manifest = json.loads((package / relative).read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("manifest must be an object")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{relative}: missing/unreadable/invalid JSON: {exc}")
            continue
        manifests[adapter] = manifest
        if manifest.get("name") != name:
            errors.append(f"{relative}: name must match folder {name}")
        if not SEMVER.fullmatch(str(manifest.get("version", ""))):
            errors.append(f"{relative}: version must be semantic version")
        for key in ("description", "license"):
            if not isinstance(manifest.get(key), str) or not manifest[key].strip():
                errors.append(f"{relative}: missing {key}")
        for key in ("skills", "apps", "mcpServers"):
            value = manifest.get(key)
            if value is None or (key == "mcpServers" and isinstance(value, dict)):
                continue
            if not isinstance(value, str) or not confined(package, value):
                errors.append(f"{relative}: {key} must be a confined ./ package path")
            elif not (package / value).exists():
                errors.append(f"{relative}: missing declared {key} path {value}")
        if adapter == ".claude-plugin" and "hooks" in manifest:
            errors.append(f"{relative}: Claude hooks use the default hooks/hooks.json, not a manifest field")

    skills_dir = package / "skills"
    skills = sorted(item.name for item in skills_dir.iterdir()
                    if item.is_dir()) if skills_dir.is_dir() else []
    if not skills:
        errors.append("package bundles no skills/<skill>/SKILL.md")
    validate_hooks(package, skills, errors)

    base = manifests.get(".claude-plugin", {})
    codex = manifests.get(".codex-plugin", {})
    if base and codex:
        for field in ("name", "version", "description", "license"):
            if codex.get(field) != base.get(field):
                errors.append(f"manifest {field} differs across host adapters")
    if codex and codex.get("skills") != "./skills/":
        errors.append("Codex skills must declare ./skills/ for the shared package layout")
    if codex:
        validate_codex_interface(codex, errors)

    cards = set()
    for skill in skills:
        card = skills_dir / skill / "SKILL.md"
        cards.add(card)
        label = f"skills/{skill}/SKILL.md"
        try:
            body = card.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"missing/unreadable {label}: {exc}")
            continue
        fields = frontmatter(body)
        if fields.get("name") != skill:
            errors.append(f"{label}: name must match its folder {skill}")
        if not SEMVER.fullmatch(fields.get("version", "")):
            errors.append(f"{label}: version must be semantic version")
        if not fields.get("license"):
            errors.append(f"{label}: missing license")
        kind = re.search(r"^\s+kind:\s*(\S+)\s*$", body.split("\n---\n", 1)[0], re.M)
        if kind and kind[1] in ("script-backed", "mixed"):
            validate_script_entrypoints(skill, card.parent, kind[1], errors)

    # Never follow links in a distributed payload. Generated trees should have
    # already materialized internal links; a dangling link is also a failure.
    for item in package.rglob("*"):
        relative = item.relative_to(package).as_posix()
        if not item.is_file():
            continue
        if item.name == "SKILL.md" and item not in cards:
            errors.append(f"additional public SKILL.md in payload: {relative}")
        if item.suffix == ".py" or (item.parent.name == "scripts" and not item.suffix):
            try:
                source = item.read_text(encoding="utf-8")
                if item.suffix == ".py" or source.startswith("#!/usr/bin/env python"):
                    ast.parse(source, filename=relative)
            except SyntaxError as exc:
                errors.append(f"invalid Python {relative}:{exc.lineno}: {exc.msg}")
            except (OSError, UnicodeError) as exc:
                errors.append(f"unreadable script {relative}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="*", type=Path, help="individual plugin directories")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="checkout or build whose plugins/skill-craft is checked")
    args = parser.parse_args()
    if args.packages:
        packages = args.packages
    else:
        leaves = sorted(path.parent.name for path in (args.root / "skills").glob("*/SKILL.md"))
        if not leaves:
            print("FAIL no source skills found", file=sys.stderr)
            return 1
        package = args.root / "plugins" / "skill-craft"
        bundled = sorted(path.parent.name for path in (package / "skills").glob("*/SKILL.md"))
        if bundled != leaves:
            print(f"FAIL skill-craft: bundles {bundled}, source has {leaves}", file=sys.stderr)
            return 1
        packages = [package]
    failed = 0
    for package in packages:
        errors = validate_package(package)
        if errors:
            failed += 1
            for error in errors:
                print(f"FAIL {package.name}: {error}", file=sys.stderr)
        else:
            print(f"OK {package.name}: complete marketplace payload")
    print(f"marketplace-packages: {len(packages) - failed}/{len(packages)} passed (offline payload validation only)")
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
