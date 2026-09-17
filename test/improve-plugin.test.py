#!/usr/bin/env python3
"""Check the two host manifests describe the same published Improve leaf."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
plugin = root / "plugins" / "improve"
claude = json.loads((plugin / ".claude-plugin/plugin.json").read_text())
codex = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
for field in ("name", "version", "description", "author", "repository", "license"):
    assert codex[field] == claude[field], f"Improve host manifest mismatch: {field}"
assert codex["skills"] == "./skills/", "Codex must discover the packaged skill tree"
assert "hooks" not in codex and "mcpServers" not in codex and "apps" not in codex
for field in (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
):
    assert codex["interface"].get(field), f"Improve Codex interface missing: {field}"
assert codex["interface"].get("capabilities"), "Improve Codex capabilities missing"
assert codex["interface"].get("defaultPrompt"), "Improve Codex default prompt missing"
assert (plugin / "LICENSE").read_bytes() == (root / "LICENSE").read_bytes()
readme = (plugin / "README.md").read_text()
assert "skills/improve/README.md" in readme, "root README must preserve authored guide location"
cards = sorted(path.relative_to(plugin).as_posix() for path in plugin.rglob("SKILL.md"))
assert cards == ["skills/improve/SKILL.md"], f"Unexpected discoverable skills: {cards}"
print("improve-plugin.test.py: PASS host metadata parity and one public skill")
