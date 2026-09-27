#!/usr/bin/env python3
"""Run the spec-judge skill headlessly: script samples, an Opus judge verdicts, script scores.

    judge_run.py --repo REPO --spec SPEC [--architecture FILE] --out DIR [--n 40]

The judge works in DIR/judge on copies (a sandboxed judge cannot read
outside its directory): repo/ (without node_modules/.git), the spec and
architecture files, and sample.json rewritten to those copies.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SKILL = ROOT / "skills" / "spec-judge"
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import hosts  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--architecture", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--model", default="claude-opus-5-5")
    args = ap.parse_args()
    judge = args.out.resolve() / "judge"
    judge.mkdir(parents=True)
    shutil.copytree(args.repo, judge / "repo", symlinks=True, ignore=shutil.ignore_patterns("node_modules", ".git"))
    shutil.copy(args.spec, judge / "spec.md")
    if args.architecture:
        shutil.copy(args.architecture, judge / "architecture.md")
    # Sample against the real checkout (git ls-files), then point the sample at the copies.
    sample_argv = [sys.executable, str(SKILL / "scripts" / "spec_judge.py"), "sample", "--repo", str(args.repo),
                   "--spec", str(args.spec), "--out", str(judge), "--n", str(args.n)]
    if args.architecture:
        sample_argv += ["--architecture", str(args.architecture)]
    subprocess.run(sample_argv, check=True, capture_output=True)
    sample = json.loads((judge / "sample.json").read_text())
    sample.update(repo="repo", spec="spec.md", architecture_file="architecture.md" if args.architecture else None)
    (judge / "sample.json").write_text(json.dumps(sample, indent=2) + "\n")
    prompt = ((SKILL / "prompts" / "judge.md").read_text()
              + "\n\nWork in the current directory: `sample.json` is here; paths in it are relative to it."
                " Write `verdicts.json` here. Do not run the score step; the harness runs it.\n")
    argv = hosts.argv_for("claude", prompt=prompt, prompt_file=args.out.resolve() / "prompt.md", cwd=judge,
                          model=args.model, effort="medium", permission_mode="acceptEdits",
                          max_turns=200, max_budget_usd=15)
    argv += ["--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    status = hosts.run_agent(argv, judge, dict(os.environ), args.out / "events.jsonl", args.out / "stderr.txt", 3600)
    if not (judge / "verdicts.json").is_file():
        print(json.dumps({"error": "judge wrote no verdicts.json", **status}))
        return 1
    score = subprocess.run([sys.executable, str(SKILL / "scripts" / "spec_judge.py"), "score", "--out", str(judge)],
                           capture_output=True, text=True)
    print(score.stdout.strip())
    return score.returncode


if __name__ == "__main__":
    raise SystemExit(main())
