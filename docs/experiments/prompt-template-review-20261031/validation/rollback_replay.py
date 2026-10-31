#!/usr/bin/env python3
"""Offline replay of the filled rollback recipe (fix 7 of the stage-prompt review) over archived isolated runs.

For every archived workspace root holding workspace.md and a decided return-plan.md, render ``rollback_lines`` with this
checkout's ShipLoop, take the working-tree recipe, and check read-only whether it would reverse cleanly: ``git diff
--binary <base> <run> -- <kept>`` piped to ``git apply -R --check`` in the source checkout (no ``--index``, so neither the
tree nor the index is touched). A run whose branch or base commit is gone, or whose plan still has an undecided path,
is reported, not scored. Usage: ``python3 rollback_replay.py [--json OUT]``.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOTS = ("~/e2e-runs", "~/e2e-runs-brownfield", "~/e2e-runs-qr", "~/e2e-runs-x4", "~/e2e-runs-owner-note")
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store
import shiploop_workspace as workspace


def git(repo: str, *args: str, data: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=False,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json")
    args = parser.parse_args()
    rows = []
    for base in ROOTS:
        for plan in sorted(glob.glob(os.path.expanduser(base) + "/**/.shiploop-runs/*/return-plan.md", recursive=True)):
            if "/test/fixtures/" in plan or "/slice/" in plan:
                continue
            root = Path(plan).parent
            row = {"root": str(root).replace(os.path.expanduser("~"), "~")}
            try:
                manifest = store.read_record(root / "workspace.md")
                lines = workspace.rollback_lines(root)
            except Exception as exc:  # noqa: BLE001 - an unreadable archive is reported, never scored
                rows.append({**row, "status": "unreadable", "detail": str(exc)[:200]})
                continue
            recipe = next(line for line in lines if "apply -R" in line).split("`")[1]
            if "<kept paths>" in recipe:
                rows.append({**row, "status": "undecided"})
                continue
            kept = shlex.split(recipe.split(" -- ", 1)[1].split(" | ", 1)[0])
            source = str(manifest.get("source") or manifest.get("source_repo") or "")
            baseline, branch = manifest["baseline_commit"], manifest["branch"]
            if not source or git(source, "rev-parse", "--verify", "-q", branch).returncode or \
                    git(source, "cat-file", "-e", baseline + "^{commit}").returncode:
                rows.append({**row, "status": "anchors-gone", "kept": len(kept)})
                continue
            diff = git(source, "diff", "--binary", baseline, branch, "--", *kept)
            if not diff.stdout.strip():
                rows.append({**row, "status": "empty-diff", "kept": len(kept)})
                continue
            check = git(source, "apply", "-R", "--check", data=diff.stdout)
            rows.append({**row, "status": "clean" if check.returncode == 0 else "conflict", "kept": len(kept),
                         "detail": check.stderr.decode(errors="replace")[:300]})
    tally: dict = {}
    for row in rows:
        tally[row["status"]] = tally.get(row["status"], 0) + 1
    scored = tally.get("clean", 0) + tally.get("conflict", 0)
    kept_counts = sorted(row["kept"] for row in rows if "kept" in row)
    print(json.dumps({"plans": len(rows), "tally": tally,
                      "clean_share_of_scored": round(tally.get("clean", 0) / scored, 3) if scored else None,
                      "kept_paths_max": kept_counts[-1] if kept_counts else None,
                      "kept_paths_median": kept_counts[len(kept_counts) // 2] if kept_counts else None}))
    for row in rows:
        if row["status"] in ("conflict", "unreadable"):
            print(row["status"], row["root"], row.get("detail", "")[:160])
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
