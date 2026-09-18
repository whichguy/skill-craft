#!/usr/bin/env python3
"""Validate complete generated packages without installing or executing skills.

This is an offline payload gate, not proof of host/model execution. Host-specific
validators and installed-consumer tests remain separate release requirements.
"""
from __future__ import annotations

import argparse
import ast
import json
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
    "devloop": {"scripts/devloop-run": "bash"},
    "evidence-gates": {"scripts/evidence-gates": "python3"},
    "improve": {
        "runtime/until-loop/scripts/until_loop_ephemeral.py": "python3",
        "runtime/until-loop/scripts/until-loop": "python3",
        "scripts/capture_evidence.py": "python3",
    },
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


def validate_package(package: Path) -> list[str]:
    """Return all actionable errors, including malformed/unreadable payloads."""
    errors: list[str] = []
    name = package.name
    if not package.is_dir() or package.is_symlink():
        return [f"{package}: package must be a real directory"]
    if not NAME.fullmatch(name):
        errors.append("package folder must be a normalized skill name")

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
        if "hooks" in manifest:
            errors.append(f"{relative}: this catalog does not distribute hooks")

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

    expected = package / "skills" / name / "SKILL.md"
    try:
        body = expected.read_text(encoding="utf-8")
        fields = frontmatter(body)
        for field in ("name", "version", "license"):
            if not fields.get(field) or fields[field] != base.get(field):
                errors.append(f"SKILL.md {field} must match the plugin manifest")
        kind = re.search(r"^\s+kind:\s*(\S+)\s*$", body.split("\n---\n", 1)[0], re.M)
        if kind and kind[1] in ("script-backed", "mixed"):
            validate_script_entrypoints(name, expected.parent, kind[1], errors)
    except (OSError, UnicodeError) as exc:
        errors.append(f"missing/unreadable skills/{name}/SKILL.md: {exc}")

    # Never follow links in a distributed payload. Generated trees should have
    # already materialized internal links; a dangling link is also a failure.
    for item in package.rglob("*"):
        relative = item.relative_to(package).as_posix()
        if not item.is_file():
            continue
        if item.name == "SKILL.md" and item != expected:
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
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="source checkout for all-leaf coverage")
    args = parser.parse_args()
    if args.packages:
        packages = args.packages
    else:
        leaves = sorted(path.parent.name for path in (args.root / "skills").glob("*/SKILL.md"))
        if not leaves:
            print("FAIL no source skills found", file=sys.stderr)
            return 1
        packages = [args.root / "plugins" / leaf for leaf in leaves]
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
