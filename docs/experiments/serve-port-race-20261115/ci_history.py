#!/usr/bin/env python3
"""How often did a candidate exit before it listened, in the CI history of this repository?

    python3 ci_history.py CACHE_DIR OUT.json [SINCE_ISO_DATE]

Run it from inside the repository (`gh` takes the repository from the current directory). It lists the runs of the ci.yml workflow
created on or after SINCE (default 2026-10-31, the day the ticket chain's calibration suites arrived), reads every attempt's jobs, and
for each job named `quick / quick` or `full / ...` downloads the job log into CACHE_DIR (read-only API calls, each log fetched once).
OUT.json gets one row per job: run, attempt, commit, event, job name, conclusion, the Node version and runner image the log names, which
of the suites that start servers through checks/serve.py printed OK or FAIL, and every line that names a port collision.
"""

import concurrent.futures
import json
from pathlib import Path
import re
import subprocess
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SUITES = ("shiploop-e2e-ticket-comments", "shiploop-e2e-ticket-sla", "shiploop-e2e-user-chain", "shiploop-e2e-user-directory",
          "shiploop-e2e-brownfield", "shiploop-e2e-brownfield-tickets", "shiploop-e2e-resources", "shiploop-e2e-quality")
RESULT = re.compile(r"^(?:\S+Z )?(OK|FAIL)\s+(\S+)\s*$")
COLLISION = re.compile(r"before it listened on PORT=\d+|did not listen on PORT=\d+|is answered by pid|EADDRINUSE|address already in use")


def gh(*args: str) -> str:
    done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise RuntimeError(f"gh {' '.join(args)}: {done.stderr.strip()[:200]}")
    return done.stdout


def log_of(repo: str, job: int, cache: Path) -> str:
    path = cache / f"{job}.log"
    if not path.exists():
        path.write_text(ANSI.sub("", gh("api", "--allow-escape-sequences", f"repos/{repo}/actions/jobs/{job}/logs")))
    return path.read_text(errors="replace")


def summarize(repo: str, cache: Path, run: dict, attempt: int, job: dict) -> dict:
    row = {"run": run["databaseId"], "attempt": attempt, "commit": run["headSha"][:8], "event": run["event"], "created": run["createdAt"],
           "job": job["name"], "job_id": job["id"], "conclusion": job["conclusion"], "started": job.get("started_at"), "suites": {},
           "collision_lines": []}
    text = log_of(repo, job["id"], cache)
    for line in text.splitlines():
        match = RESULT.match(line.strip())
        if match and match.group(2) in SUITES:
            row["suites"][match.group(2)] = match.group(1)
        if COLLISION.search(line) and len(row["collision_lines"]) < 6:
            row["collision_lines"].append(line.strip()[:300])
    node = re.search(r"node: (v[0-9][^\s]*)", text)
    image = re.search(r"Image: (ubuntu-[0-9.]+)", text)
    row["node"], row["image"] = (node.group(1) if node else None), (image.group(1) if image else None)
    return row


def summarize_safely(repo: str, cache: Path, run: dict, attempt: int, job: dict) -> dict:
    """summarize(), or a row that says why the log could not be read (a job whose log has expired or cannot be fetched)."""
    try:
        return summarize(repo, cache, run, attempt, job)
    except (RuntimeError, subprocess.TimeoutExpired) as why:
        return {"run": run["databaseId"], "attempt": attempt, "commit": run["headSha"][:8], "job": job["name"], "job_id": job["id"],
                "conclusion": job["conclusion"], "unread": str(why)[:200]}


def main() -> None:
    cache, out = Path(sys.argv[1]), Path(sys.argv[2])
    since = sys.argv[3] if len(sys.argv) > 3 else "2026-10-31"
    cache.mkdir(parents=True, exist_ok=True)
    repo = json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]
    runs = [r for r in json.loads(gh("run", "list", "--workflow", "ci.yml", "--limit", "1000", "--json",
                                     "databaseId,event,headSha,createdAt,attempt,conclusion")) if r["createdAt"][:10] >= since]
    print(f"{len(runs)} runs since {since}", file=sys.stderr)
    work = []
    for run in runs:
        for attempt in range(1, run["attempt"] + 1):
            work.append((run, attempt))

    def jobs_of(item):
        run, attempt = item
        data = json.loads(gh("api", f"repos/{repo}/actions/runs/{run['databaseId']}/attempts/{attempt}/jobs?per_page=100"))
        return [(run, attempt, job) for job in data["jobs"] if job["name"].startswith(("quick /", "full /")) and job["conclusion"] in ("success", "failure")]

    rows, todo = [], []
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        for found in pool.map(jobs_of, work):
            todo.extend(found)
        print(f"{len(todo)} jobs to read", file=sys.stderr)
        for done, row in enumerate(pool.map(lambda item: summarize_safely(repo, cache, *item), todo), 1):
            rows.append(row)
            if done % 50 == 0:
                print(f"  {done}/{len(todo)}", file=sys.stderr)
    out.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(rows)} rows to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
