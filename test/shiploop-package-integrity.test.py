#!/usr/bin/env python3
"""Static integrity of the ShipLoop package: links, reachability, hooks, syntax.

Prompt and reference edits reach models through links a script or card names;
nothing else checks that those links still resolve or that every reference is
still reachable.  These checks read files only: no model, host or run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills" / "shiploop"

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_HOOK_EVENTS = {"after-shell", "turn-end"}


def _texts(package: Path) -> dict[Path, str]:
    return {
        path: path.read_text(errors="ignore")
        for path in package.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def broken_links(package: Path) -> list[str]:
    """Relative Markdown links whose target file does not exist."""

    broken = []
    for path, text in _texts(package).items():
        if path.suffix != ".md":
            continue
        for match in _LINK.finditer(text):
            target = match.group(1).split("#", 1)[0]
            if not target or re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith(("/", "<")):
                continue
            if not (path.parent / target).exists():
                broken.append(f"{path.relative_to(package)} -> {match.group(1)}")
    return sorted(broken)


def orphaned_references(package: Path) -> list[str]:
    """Reference files that no entry point reaches by name, directly or through another reference.

    Entry points are what a host or reader opens first: the card, the README,
    commands, scripts, hooks and the hook manifest.
    """

    texts = _texts(package)
    references = {path for path in texts if path.is_relative_to(package / "references")}
    roots = [path for path in texts
             if path.name in {"SKILL.md", "README.md", "host-hooks.json"} and path.parent == package
             or path.parent.name in {"scripts", "commands", "hooks"}]
    seen, stack = set(roots), list(roots)
    while stack:
        text = texts[stack.pop()]
        for reference in references - seen:
            if reference.name in text or reference.relative_to(package / "references").as_posix() in text:
                seen.add(reference)
                stack.append(reference)
    return sorted(path.relative_to(package).as_posix() for path in references - seen)


def hook_manifest_problems(package: Path) -> list[str]:
    problems = []
    manifest = json.loads((package / "host-hooks.json").read_text())
    ids = [hook.get("id") for hook in manifest["hooks"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate hook id")
    for hook in manifest["hooks"]:
        script = package / hook["script"]
        if not script.is_file():
            problems.append(f"{hook['id']}: missing {hook['script']}")
        elif not os.access(script, os.X_OK):
            problems.append(f"{hook['id']}: {hook['script']} is not executable")
        if hook["event"] not in _HOOK_EVENTS:
            problems.append(f"{hook['id']}: unknown event {hook['event']}")
        if not hook.get("hosts") or not isinstance(hook.get("timeout"), int) or hook["timeout"] <= 0:
            problems.append(f"{hook['id']}: needs hosts and a positive timeout")
    return problems


def python_script_problems(package: Path) -> list[str]:
    """Python sources that do not compile, and entry scripts that are not executable."""

    problems = []
    for path in sorted((package / "scripts").iterdir()):
        if not path.is_file():
            continue
        source = path.read_text(errors="ignore")
        entry = path.suffix == ""
        if entry and not source.startswith("#!/usr/bin/env python3"):
            continue
        if entry and not os.access(path, os.X_OK):
            problems.append(f"{path.name}: entry script is not executable")
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            problems.append(f"{path.name}: {exc.msg} (line {exc.lineno})")
    return problems


class PackageIntegrityTests(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self) -> None:
        self.assertEqual(broken_links(PACKAGE), [])

    def test_every_reference_is_reachable_from_an_entry_point(self) -> None:
        self.assertEqual(orphaned_references(PACKAGE), [])

    def test_hook_manifest_names_executable_scripts_for_known_events(self) -> None:
        self.assertEqual(hook_manifest_problems(PACKAGE), [])

    def test_python_scripts_compile_and_entry_scripts_are_executable(self) -> None:
        self.assertEqual(python_script_problems(PACKAGE), [])

    def test_graph_dry_run_scenario_is_valid_json(self) -> None:
        json.loads((PACKAGE / "references" / "graph-dry-run-scenario.json").read_text())

    @unittest.skipUnless(shutil.which("node"), "node is required for the OpenCode hook")
    def test_opencode_keepalive_hook_is_valid_module_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "opencode-keepalive.mjs"
            shutil.copyfile(PACKAGE / "hooks" / "opencode-keepalive.js", module)
            result = subprocess.run(["node", "--check", str(module)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class CheckerSensitivityTests(unittest.TestCase):
    """Each check must fail on a package with the defect it looks for."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.package = Path(tmp.name) / "shiploop"
        (self.package / "references").mkdir(parents=True)
        (self.package / "scripts").mkdir()
        (self.package / "SKILL.md").write_text("See [guide](references/guide.md).\n")
        (self.package / "references" / "guide.md").write_text("Also [missing](gone.md#part).\n")
        (self.package / "references" / "lonely.md").write_text("nobody links here\n")
        hook = self.package / "scripts" / "shiploop-hook"
        hook.write_text("#!/usr/bin/env python3\nprint(\n")
        (self.package / "host-hooks.json").write_text(json.dumps({"hooks": [
            {"id": "a", "event": "after-shell", "script": "scripts/shiploop-hook", "timeout": 5, "hosts": ["claude"]},
            {"id": "b", "event": "session-start", "script": "scripts/absent", "timeout": 0, "hosts": []},
        ]}))

    def test_each_defect_is_reported(self) -> None:
        self.assertEqual(broken_links(self.package), ["references/guide.md -> gone.md#part"])
        self.assertEqual(orphaned_references(self.package), ["references/lonely.md"])
        problems = hook_manifest_problems(self.package)
        self.assertIn("a: scripts/shiploop-hook is not executable", problems)
        self.assertIn("b: missing scripts/absent", problems)
        self.assertIn("b: unknown event session-start", problems)
        self.assertIn("b: needs hosts and a positive timeout", problems)
        script_problems = python_script_problems(self.package)
        self.assertIn("shiploop-hook: entry script is not executable", script_problems)
        self.assertTrue(any(problem.startswith("shiploop-hook: ") and "line" in problem
                            for problem in script_problems), script_problems)


if __name__ == "__main__":
    unittest.main()
