#!/usr/bin/env python3
"""Apply a text patch to one file of a plugin BUILD copy (round 9's card arm). Never the source checkout.

PATCH.json: {"about": ..., "file": "<path inside the plugin>", "edits": [{"old": ..., "new": ...}, ...]}. Every `old`
must occur exactly once in the file, or nothing is written.

Usage: python3 card_patch.py PLUGIN_DIR PATCH.json
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]


def main(plugin, patch):
    plugin = pathlib.Path(plugin).resolve()
    if REPO in plugin.parents or plugin == REPO:
        raise SystemExit("card_patch.py edits a build copy, not this checkout")
    spec = json.loads(pathlib.Path(patch).read_text())
    target = plugin / spec["file"]
    text = target.read_text()
    for edit in spec["edits"]:
        if text.count(edit["old"]) != 1:
            raise SystemExit(f"not applied: this text occurs {text.count(edit['old'])} times in {target}: {edit['old'][:70]!r}")
        text = text.replace(edit["old"], edit["new"])
    target.write_text(text)
    print(f"{len(spec['edits'])} edits applied to {target}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
