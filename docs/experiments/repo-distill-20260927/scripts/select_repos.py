#!/usr/bin/env python3
"""Walk the most-starred JavaScript/TypeScript repositories in descending
order and report each against the case gates; the first to pass is the pick.

    select_repos.py --out DIR [--limit N] [--max-own 10000]

Gates, cheapest first (API metadata, then package.json, then a shallow
clone): maintained (pushed within a year, not archived, not a fork); a
rebuildable interface (package.json `bin`, i.e. a CLI or a server started
from one); not a monorepo, no git submodules and no runtime dependency published from the
same owner's other repos (an aggregation of repos); has its own tests;
material own logic
(repo_value.py: own code >= 1,000 lines) and a feasible size (<= --max-own).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gh(*args: str):
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else None


def top(language: str, pages: int) -> list[dict]:
    repos = []
    for page in range(1, pages + 1):
        data = gh(f"search/repositories?q=language:{language}+stars:>5000&sort=stars&order=desc"
                  f"&per_page=100&page={page}")
        repos += (data or {}).get("items", [])
    return repos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pages", type=int, default=2, help="100 repos per page per language")
    ap.add_argument("--max-own", type=int, default=10000)
    ap.add_argument("--stop-after", type=int, default=3, help="stop after this many passes")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    seen, repos = set(), []
    for lang in ("TypeScript", "JavaScript"):
        for r in top(lang, args.pages):
            if r["full_name"] not in seen:
                seen.add(r["full_name"])
                repos.append(r)
    repos.sort(key=lambda r: -r["stargazers_count"])
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).isoformat()
    rows, passed = [], []
    for r in repos:
        row = {"repo": r["full_name"], "stars": r["stargazers_count"]}
        rows.append(row)
        if r["archived"] or r["fork"] or r["pushed_at"] < cutoff:
            row["verdict"] = "unmaintained/archived/fork"
            continue
        pkg_meta = gh(f"repos/{r['full_name']}/contents/package.json")
        if not pkg_meta or "content" not in pkg_meta:
            row["verdict"] = "no root package.json"
            continue
        pkg = json.loads(base64.b64decode(pkg_meta["content"]))
        if pkg.get("workspaces"):
            row["verdict"] = "monorepo"
            continue
        if not pkg.get("bin"):
            row["verdict"] = "no bin (library/framework/app without a CLI)"
            continue
        clone = args.out / "clones" / r["full_name"].replace("/", "__")
        if not clone.exists():
            subprocess.run(["git", "clone", "-q", "--depth", "1", r["clone_url"], str(clone)],
                           capture_output=True)
        tests = subprocess.run(["git", "-C", str(clone), "ls-files"], capture_output=True,
                               text=True).stdout
        if not any(p in tests for p in ("test/", "tests/", "__tests__/", ".test.", ".spec.")):
            row["verdict"] = "no tests"
            continue
        value = subprocess.run([sys.executable, str(HERE / "repo_value.py"), str(clone)],
                               capture_output=True, text=True)
        v = json.loads(value.stdout) if value.stdout.strip().startswith("{") else {}
        row.update({k: v.get(k) for k in ("own_code_lines", "runtime_deps", "workspaces")})
        owner = r["full_name"].split("/")[0].lower()
        siblings = [d for d in pkg.get("dependencies", {}) if owner in json.dumps(
            json.loads(subprocess.run(["npm", "view", d, "repository.url", "--json"], capture_output=True,
                                      text=True).stdout or "null")).lower()]
        row["same_owner_deps"] = siblings
        if v.get("workspaces"):
            row["verdict"] = "monorepo"
        elif (clone / ".gitmodules").is_file():
            row["verdict"] = "aggregates other repos (git submodules)"
        elif siblings:
            row["verdict"] = f"aggregates its owner's other repos ({len(siblings)} deps)"
        elif (v.get("own_code_lines") or 0) < 1000:
            row["verdict"] = "thin (< 1,000 own lines)"
        elif v["own_code_lines"] > args.max_own:
            row["verdict"] = f"too large (> {args.max_own} own lines)"
        else:
            row["verdict"] = "PASS"
            passed.append(row)
            if len(passed) >= args.stop_after:
                break
    (args.out / "selection.json").write_text(json.dumps(rows, indent=2) + "\n")
    for row in rows:
        print(f"{row['stars']:>7}  {row['repo']:<45} {row['verdict']}"
              + (f"  own={row.get('own_code_lines')} deps={row.get('runtime_deps')}" if "own_code_lines" in row else "")
              + (f" same-owner={row['same_owner_deps']}" if row.get("same_owner_deps") else ""))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
