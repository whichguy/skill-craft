#!/usr/bin/env python3
"""Build this checkout's plugin into a folder and apply one overlay to the copy, for a whole-delivery arm (round 7).

run.py takes no overlay, but it takes a built plugin: `run.py --source checkout --plugin-dir <printed path>`. The
checkout itself is never changed. With no overlay the build is the checkout as it is.

Usage: python3 build_arm.py ARM_FOLDER [OVERLAY.json]      prints the plugin folder
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import overlay as overlays
import run


def main(folder, overlay=None):
    out = pathlib.Path(folder).resolve()
    out.mkdir(parents=True, exist_ok=False)
    plugin = run.build_candidate(out)
    applied = overlays.apply_to_plugin(pathlib.Path(overlay).resolve(), plugin) if overlay else None
    (out / "arm.json").write_text(json.dumps({"plugin": str(plugin), "overlay": applied}, indent=1) + "\n")
    print(plugin)


if __name__ == "__main__":
    main(*sys.argv[1:3])
