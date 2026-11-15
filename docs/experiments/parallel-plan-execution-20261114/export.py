#!/usr/bin/env python3
"""export.py: copy trials' compact evidence into the repository (the owner's rule: evidence lives in the repo).

Apparatus for docs/experiments/parallel-plan-execution-20261114. Per trial it keeps the ledger, the plan, the packet, the
invocation record, score.json, timeline.txt, gantt.txt, the host's native agent record (native.json) and a trimmed copy of the host's raw events (every string cut to
600 characters, signatures dropped, so the stream's shape and timing stay and bulk text goes). The profile directory
(home/) and full stderr are not copied; stderr keeps its last 4 KB.

  export.py TRIAL... [--to DIR]       DIR defaults to this folder's evidence/ (never a folder named results/)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402

LIMIT = 600


def trim(obj):
    if isinstance(obj, str):
        return obj if len(obj) <= LIMIT else obj[:LIMIT] + f"...[+{len(obj) - LIMIT} chars]"
    if isinstance(obj, list):
        return [trim(x) for x in obj]
    if isinstance(obj, dict):
        return {k: ("<dropped>" if k == "signature" else trim(v)) for k, v in obj.items()}
    return obj


def export(trial: Path, dest_root: Path) -> Path:
    dest = dest_root / trial.name
    dest.mkdir(parents=True, exist_ok=False)
    for name in ("packet.md", "invocation.json", "score.json", "timeline.txt", "gantt.txt"):
        if (trial / name).is_file():
            shutil.copy(trial / name, dest / name)
    for src, name in (("work/run/ledger.jsonl", "ledger.jsonl"), ("work/plan.json", "plan.json")):
        if (trial / src).is_file():
            shutil.copy(trial / src, dest / name)
    events = trial / "events.raw.jsonl"
    if events.is_file():
        with open(dest / "events.trimmed.jsonl", "w") as out:
            for line in events.read_text(errors="replace").splitlines():
                try:
                    out.write(json.dumps(trim(json.loads(line)), separators=(",", ":")) + "\n")
                except ValueError:
                    out.write(json.dumps({"raw": line[:LIMIT]}) + "\n")
    host = json.loads((trial / "invocation.json").read_text()).get("host") if (trial / "invocation.json").is_file() else None
    if host:   # the host's own account of its sub-agents (rollout calls and log lines are cut; the ids are the host's own)
        (dest / "native.json").write_text(json.dumps(score.native_agents(trial, host), indent=1, default=str) + "\n")
    repo = trial / "work" / "repo"
    if (repo / ".git").exists():   # a write trial: the history, the file list and the code the workers wrote (README Amendment A10)
        git = ["git", "-C", str(repo)]
        parts = [f"$ git {' '.join(c)}\n" + subprocess.run(git + c, capture_output=True, text=True).stdout
                 for c in (["log", "--all", "--graph", "--oneline", "--decorate"], ["ls-files"], ["status", "--short"], ["branch", "-a"])]
        (dest / "repo.txt").write_text("\n".join(parts))
        for sub_dir in ("pkg", "tests"):
            for src in (repo / sub_dir).glob("*.py"):
                (dest / "final-tree" / sub_dir).mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest / "final-tree" / sub_dir / src.name)
    if (trial / "work" / "plan.json").is_file() and json.loads((trial / "work" / "plan.json").read_text()).get("fixture") == "tickets":
        export_real(trial, dest)
    err = trial / "stderr.txt"
    if err.is_file():
        (dest / "stderr.tail.txt").write_text(err.read_text(errors="replace")[-4096:])
    return dest


def export_real(trial: Path, dest: Path) -> None:
    """A real-repository trial (README Amendment A14): the code the workers wrote as diffs, not the whole service (which is the base's, in
    the harness's fixtures): final.diff (the base to the final tree, staged first because a shared run leaves its changes uncommitted) and, in an
    isolated run, attempts/<task>-<n>.diff (each attempt's branch against the commit it started from, a fix attempt against main as it was)."""
    repo = trial / "work" / "repo"
    git = ["git", "-C", str(repo)]
    base = subprocess.run(git + ["rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True).stdout.split()[0]
    subprocess.run(git + ["add", "-A"], capture_output=True)
    (dest / "final.diff").write_text(subprocess.run(git + ["diff", "--cached", "--no-color", base], capture_output=True, text=True).stdout)
    ledger = [json.loads(line) for line in (trial / "work" / "run" / "ledger.jsonl").read_text().splitlines() if line.strip()]
    for e in ledger:
        d = e["detail"]
        if e["kind"] == "workspace" and d.get("mode") == "isolated" and d.get("branch"):
            (dest / "attempts").mkdir(exist_ok=True)
            diff = subprocess.run(git + ["diff", "--no-color", d["base"], d["branch"]], capture_output=True, text=True).stdout
            (dest / "attempts" / f"{e['step']}-{d['attempt']}.diff").write_text(diff)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trials", nargs="+")
    parser.add_argument("--to", default=str(HERE / "evidence"))
    args = parser.parse_args(argv)
    for t in args.trials:
        print(export(Path(t).resolve(), Path(args.to)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
