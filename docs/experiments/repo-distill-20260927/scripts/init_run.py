#!/usr/bin/env python3
"""Initializer distill of one repository in a temporary clone.

    init_run.py --repo OWNER/NAME --out DIR [--commit SHA] [--model gpt-6-luna] [--effort xhigh]

Clones the repository into DIR/repo (pinned to --commit, else the default
branch head, recorded), runs skills/repo-distill/prompts/initialize.md there
with one isolated Codex session, and checks the result: docs/shiploop/ has
the five files, and nothing outside docs/shiploop/ changed. Writes
DIR/init.json. The clone and its output are disposable.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rebuild import codex_step  # noqa: E402

PROMPT = HERE.parents[3] / "skills" / "repo-distill" / "prompts" / "initialize.md"
FILES = ("README.md", "spec.md", "architecture.md", "environment.md", "test-strategy.md")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--commit")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--effort", default="xhigh")
    args = ap.parse_args()
    out = args.out.resolve()
    repo = out / "repo"
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", f"https://github.com/{args.repo}", str(repo)], check=True)
    if args.commit:
        git(repo, "checkout", "-q", args.commit)
    commit = git(repo, "rev-parse", "HEAD")
    codex_step(repo, out / "step", args.model, args.effort, PROMPT)
    home = repo / "docs" / "shiploop"
    changed = [line[3:] for line in git(repo, "status", "--porcelain", "--untracked-files=all").splitlines()]
    outside = [p for p in changed if not p.startswith("docs/shiploop/")
               and not p.startswith("node_modules") and "package-lock" not in p]
    step = json.loads((out / "step" / "step.json").read_text())
    report = {"repo": args.repo, "commit": commit, "model": args.model, "effort": args.effort,
              "files": {f: (home / f).is_file() for f in FILES}, "changed_outside_home": outside[:20],
              "requirements": len(set(__import__("re").findall(r"\bR-\d+\b", (home / "spec.md").read_text())))
              if (home / "spec.md").is_file() else 0,
              "step": {k: step.get(k) for k in ("status", "elapsed_seconds", "turns", "commands", "usage")}}
    report["ok"] = all(report["files"].values()) and not outside and step.get("status") == "exited"
    (out / "init.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
