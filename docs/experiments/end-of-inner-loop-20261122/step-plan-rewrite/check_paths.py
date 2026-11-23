#!/usr/bin/env python3
"""Every absolute /Users/ path a sample of either scenario could be shown: build both as a live sample is built, issue the packet, and search
every file of the built tree (product checkout, execution checkout, run directory, the packet, the plugin build), every commit, and the
opening prompt. A path inside the sample's own folder is its own; every other one is listed. No model. Exit 1 when one outside is left in
anything the model is given (the packet, the prompt, either checkout, the run directory, a commit). Listed but not counted: the plugin build
(the same for every run of that ShipLoop) and ``.stage-suite/`` (the builder's own working files beside the checkout, which nothing names).

    python3 check_paths.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "test/shiploop_e2e/stage_suite"), str(ROOT / "test/shiploop_e2e")]
import run  # noqa: E402
import stage_build as sb  # noqa: E402

CASE = json.loads((HERE / "case.json").read_text())
PATH = re.compile(rb"/Users/[^\s\"'`,;)<>\\]*")


def outside(data: bytes, own: bytes) -> list[str]:
    return [m.decode(errors="replace") for m in PATH.findall(data) if not m.startswith(own)]


def main() -> None:
    bad = 0
    with tempfile.TemporaryDirectory(prefix="spr-paths-") as temp:
        for name in (CASE["requirement_scenario"], CASE["proof_scenario"]):
            out = Path(temp).resolve() / name / "1"
            out.mkdir(parents=True)
            plugin = run.build_candidate(out)
            cli = run.shiploop_cli(plugin)
            sc = sb.load("step-plan/" + name, HERE / "stage_cases")
            bundle = sb.render(sc, out, cli=cli)
            own, files, found = str(out).encode(), Counter(), Counter()
            for path in sorted(out.rglob("*")):
                part = path.relative_to(out).parts
                if path.is_symlink() or not path.is_file() or ".git" in part:
                    continue
                area = "plugin build" if part[0] == "build" else "/".join(part[:3]) if part[0] == ".shiploop-runs" else part[0]
                files[area] += 1
                for text in outside(path.read_bytes(), own):
                    found[(area, str(path.relative_to(out)), text)] += 1
            commits = 0
            for tree in (out / "work", bundle.tree):
                revisions = subprocess.run(["git", "-C", str(tree), "rev-list", "--all"], capture_output=True, text=True, check=True).stdout.split()
                commits += len(revisions)
                log = subprocess.run(["git", "-C", str(tree), "log", "--all", "-p", "--format=%B"], capture_output=True, check=True).stdout
                for text in outside(log, own):
                    found[("commits", tree.name, text)] += 1
            prompt = run.seed_prompt(cli, str(bundle.run_dir), sc.data["request"]["prompt"], "inline", "step-plan").encode()
            for label, data in (("packet file", bundle.packet.encode()), ("printed packet", bundle.packet_head.encode()), ("opening prompt", prompt)):
                for text in outside(data, own):
                    found[(label, "-", text)] += 1
                print(f"{name}: {label}: {len(PATH.findall(data))} /Users/ paths, {len(outside(data, own))} outside the sample")
            print(f"{name}: files searched {dict(files)}, commits {commits}; outside the sample:")
            for (area, where, text), times in sorted(found.items()):
                print(f"    [{area}] {where}: {text} x{times}")
            print("    none" if not found else f"    {len(found)} in all")
            bad += sum(1 for area, _where, _text in found if area not in ("plugin build", ".stage-suite"))
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
