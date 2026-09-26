#!/usr/bin/env python3
"""Check the two host manifests describe the same published skill-craft
package, and that Improve ships correctly inside it."""
import json
from pathlib import Path

import package_build

root = Path(__file__).resolve().parents[1]
# plugins/ is release output; package tests read a build of the current source.
PLUGINS = package_build.plugins()
plugin = PLUGINS / "skill-craft"
claude = json.loads((plugin / ".claude-plugin/plugin.json").read_text())
codex = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
for field in ("name", "version", "description", "author", "repository", "license"):
    assert codex[field] == claude[field], f"skill-craft host manifest mismatch: {field}"
assert codex["skills"] == "./skills/", "Codex must discover the packaged skill tree"
assert "mcpServers" not in codex and "apps" not in codex
for field in (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
):
    assert codex["interface"].get(field), f"skill-craft Codex interface missing: {field}"
assert codex["interface"].get("capabilities"), "skill-craft Codex capabilities missing"
assert codex["interface"].get("defaultPrompt"), "skill-craft Codex default prompt missing"
assert (plugin / "LICENSE").read_bytes() == (root / "LICENSE").read_bytes()
readme = (plugin / "README.md").read_text()
assert "skills/improve/SKILL.md" in readme, "package README must list the Improve skill"
improve_skill = plugin / "skills/improve/SKILL.md"
assert improve_skill.is_file(), "Improve must publish inside the shared skill-craft package"
assert (plugin / "skills/improve/README.md").is_file(), \
    "Improve's authored guide must still ship inside the package"
cards = sorted(path.relative_to(plugin).as_posix() for path in plugin.rglob("SKILL.md"))
assert "skills/improve/SKILL.md" in cards, f"Improve missing from discoverable skills: {cards}"
print("improve-plugin.test.py: PASS host metadata parity and Improve ships in skill-craft")
