#!/usr/bin/env python3
"""Attribute each failing oracle check to where it was lost (one Opus judge).

    attribute.py --original REPO --spec SPEC --rebuild WORK --oracle DIR --scored DIR --out DIR

--scored holds results.json and oracle.tap from the rebuild's oracle run. The
judge sees links to everything in one directory and writes attribution.json;
this script then checks every failing test is attributed exactly once.
"""

from __future__ import annotations

import argparse
import shutil
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "test" / "shiploop_e2e"))

import hosts  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    for name in ("original", "spec", "rebuild", "oracle", "scored", "out"):
        ap.add_argument(f"--{name}", type=Path, required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    args = ap.parse_args()
    out = args.out.resolve()
    judge = out / "judge"
    judge.mkdir(parents=True)
    # Real copies, not links: a sandboxed judge may not read outside its
    # directory. Dependencies are left out of the original and the rebuild.
    for name, source in {"original": args.original, "spec.md": args.spec, "rebuild": args.rebuild,
                         "oracle": args.oracle, "results.json": args.scored / "results.json",
                         "oracle.tap": args.scored / "oracle.tap"}.items():
        if source.is_dir():
            shutil.copytree(source, judge / name, symlinks=True,
                            ignore=shutil.ignore_patterns("node_modules", ".git"))
        else:
            shutil.copy(source, judge / name)
    failing = sorted(k for k, v in json.loads((args.scored / "results.json").read_text())["tests"].items()
                     if v == "fail")
    if not failing:
        print(json.dumps({"failures": 0}))
        return 0
    prompt = (HERE.parent / "prompts" / "attribute.md").read_text()
    argv = hosts.argv_for("claude", prompt=prompt, prompt_file=out / "prompt.md", cwd=judge,
                          model=args.model, effort=args.effort, permission_mode="acceptEdits",
                          max_turns=120, max_budget_usd=15)
    argv += ["--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    status = hosts.run_agent(argv, judge, dict(os.environ), out / "events.jsonl",
                             out / "stderr.txt", 3600)
    report = judge / "attribution.json"
    if not report.is_file():
        print(json.dumps({"error": "judge wrote no attribution.json", **status}))
        return 1
    data = json.loads(report.read_text())
    named = [f.get("test") for f in data.get("failures", [])]
    missing = [t for t in failing if not any(t == n or t.endswith(str(n)) for n in named)]
    locations: dict = {}
    for f in data.get("failures", []):
        locations[f.get("location")] = locations.get(f.get("location"), 0) + 1
    summary = {**status, "failing": len(failing), "attributed": len(named), "missing": missing,
               "locations": locations, "root_causes": len(data.get("root_causes", []))}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
