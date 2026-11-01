"""Tally the follow-on list over the ShipLoop runs under one or more folders: design M3, "log the list on the owner's real runs without acting
on it, and count how often a recommended follow-on is started".

Usage: python3 tally_follow_on.py ROOT [ROOT ...] [--json]
       python3 tally_follow_on.py --self-test

A ROOT is any folder under which ShipLoop kept runs as `.shiploop-runs/<id>/run/state.md`: the folder that holds a project's
`.shiploop-runs` (its parent, for an isolated run), an E2E output folder, or the E2E runs root.  It is searched without entering
`work`, `home`, `worktree`, `.git` or `node_modules`.  Read-only; it calls nothing and computes only counts.

What it counts, per ROOT and in total:
- runs, by ShipLoop status (done, blocked, active, ...);
- runs whose accepted handoff carries `follow_on` ("recorded") and runs whose handoff has none ("not recorded": an older build, or no
  handoff yet, which is not the same as none);
- the entries by class, and the runs that recommend a follow-on run (a `gap` or a `decision`);
- the recommended runs that were started: a later run whose prompt begins with the recommending run's `follow-on-request.md`, ignoring
  the final newline and the skill invocation a host adds (`$skill-craft:shiploop `); each pair names the started run's status.
The count of starts is the demand signal of M3.  It cannot tell a person who started the run from a script; that is the user's reading.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

SKIP = {"work", "home", "worktree", ".git", "node_modules", "__pycache__"}
INVOCATION = re.compile(r"^[$/](?:skill-craft:)?shiploop\s+")
RECOMMEND = ("gap", "decision")


def read_state(path: Path) -> dict:
    match = re.search(r"```[a-z-]*\n(.*?)\n```", path.read_text(encoding="utf-8", errors="replace"), re.DOTALL)
    try:
        return json.loads(match.group(1)) if match else {}
    except ValueError:
        return {}


def run_folders(root: Path) -> list[Path]:
    """Every `<...>/.shiploop-runs/<id>/run` folder under root that holds a state.md."""
    found = []
    for folder, names, _files in os.walk(root):
        if os.path.basename(folder) == ".shiploop-runs":
            for run_id in sorted(names):
                run = Path(folder) / run_id / "run"
                if (run / "state.md").is_file():
                    found.append(run)
            names[:] = []
            continue
        names[:] = sorted(name for name in names if name not in SKIP)
    return found


def handoff_list(state: dict):
    """The accepted handoff's follow_on (None when no handoff is accepted or its result has no key)."""
    rows = [row for row in state.get("history", []) if row.get("stage") == "handoff" and row.get("outcome") == "done"]
    if not rows:
        return None
    result = state.get("accepted", {}).get(rows[-1].get("action"), {})
    entries = result.get("follow_on") if isinstance(result, dict) else None
    return list(entries) if isinstance(entries, list) else None


def prompt_text(state: dict) -> str:
    return INVOCATION.sub("", str(state.get("prompt", "")), count=1).rstrip("\n")


def describe(run: Path) -> dict:
    state = read_state(run / "state.md")
    entries = handoff_list(state)
    request = run / "follow-on-request.md"
    return {"run": str(run), "status": state.get("status"), "recorded": entries is not None,
            "classes": [str(entry.get("class")) for entry in entries or []],
            "recommends": any(str(entry.get("class")) in RECOMMEND for entry in entries or []),
            "request": request.read_text(encoding="utf-8").rstrip("\n") if request.is_file() else None,
            "prompt": prompt_text(state)}


def tally(roots: list[Path]) -> dict:
    runs = [describe(run) for root in roots for run in run_folders(root)]
    classes = Counter(cls for row in runs for cls in row["classes"])
    pairs = []
    for row in runs:
        if not row["request"]:
            continue
        for other in runs:
            if other is not row and other["prompt"].startswith(row["request"]):
                pairs.append({"recommended_by": row["run"], "started": other["run"], "started_status": other["status"]})
    recommending = [row for row in runs if row["recommends"]]
    started_from = {pair["recommended_by"] for pair in pairs}
    return {"roots": [str(root) for root in roots], "runs": len(runs), "by_status": dict(Counter(str(row["status"]) for row in runs)),
            "follow_on_recorded": sum(row["recorded"] for row in runs),
            "follow_on_not_recorded": sum(not row["recorded"] for row in runs),
            "runs_with_a_non_empty_list": sum(bool(row["classes"]) for row in runs), "entries_by_class": dict(classes),
            "runs_recommending_a_follow_on": len(recommending),
            "recommending_runs_with_a_started_follow_on": sum(row["run"] in started_from for row in recommending),
            "started_follow_on_runs": len(pairs), "started_by_status": dict(Counter(str(pair["started_status"]) for pair in pairs)),
            "pairs": pairs}


def show(result: dict) -> None:
    print("roots:", ", ".join(result["roots"]))
    print(f"runs: {result['runs']}  by status: {result['by_status']}")
    print(f"follow_on recorded: {result['follow_on_recorded']}  not recorded: {result['follow_on_not_recorded']} "
          "(older build or no handoff yet: unmeasured, not none)")
    print(f"runs with a non-empty list: {result['runs_with_a_non_empty_list']}  entries by class: {result['entries_by_class']}")
    print(f"runs that recommend a follow-on run (gap or decision): {result['runs_recommending_a_follow_on']}")
    print(f"  of those, with a follow-on run started: {result['recommending_runs_with_a_started_follow_on']}  "
          f"(started runs: {result['started_follow_on_runs']}, by status: {result['started_by_status']})")
    for pair in result["pairs"]:
        print("   ", pair["recommended_by"].split(".shiploop-runs/")[-1], "->", pair["started"].split(".shiploop-runs/")[-1], f"[{pair['started_status']}]")


def self_test() -> None:
    def make(root: Path, run_id: str, status: str, entries, prompt: str, request: str | None = None) -> None:
        run = root / ".shiploop-runs" / run_id / "run"
        run.mkdir(parents=True)
        state = {"status": status, "prompt": prompt, "history": [], "accepted": {}}
        if entries is not None:
            state["history"] = [{"stage": "handoff", "outcome": "done", "action": "a1"}]
            state["accepted"] = {"a1": {"follow_on": entries}}
        (run / "state.md").write_text("# state\n\n```json\n" + json.dumps(state) + "\n```\n", encoding="utf-8")
        if request is not None:
            (run / "follow-on-request.md").write_text(request, encoding="utf-8")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        gap = {"class": "gap"}
        note = {"class": "note"}
        text = "Follow up an earlier run.\n- Gap, S3: the option.\n"
        make(root, "p-1", "done", [gap, note], "Write a tool.", request=text)          # recommends; started twice below
        make(root, "p-2", "done", [note], "Write another tool.")                          # a note only: recommends nothing
        make(root, "p-3", "done", None, "An older run.")                                   # no list: not recorded
        make(root, "p-4", "done", [], "$skill-craft:shiploop " + text.rstrip("\n"))        # a host-started follow-on, list empty
        make(root, "p-5", "blocked", None, text.rstrip("\n") + "\nThe requester's answer.")  # a started run that asked and stopped
        (root / "work" / ".shiploop-runs" / "x-1" / "run").mkdir(parents=True)             # inside a skipped folder: never read
        (root / "work" / ".shiploop-runs" / "x-1" / "run" / "state.md").write_text("```json\n{}\n```\n", encoding="utf-8")
        result = tally([root])
    assert result["runs"] == 5, result
    assert result["follow_on_recorded"] == 3 and result["follow_on_not_recorded"] == 2, result
    assert result["entries_by_class"] == {"gap": 1, "note": 2}, result
    assert result["runs_recommending_a_follow_on"] == 1 and result["recommending_runs_with_a_started_follow_on"] == 1, result
    assert result["started_follow_on_runs"] == 2 and result["started_by_status"] == {"done": 1, "blocked": 1}, result
    print("self-test ok")


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        self_test()
        return 0
    roots = [Path(arg).expanduser().resolve() for arg in argv if not arg.startswith("--")]
    if not roots:
        print(__doc__)
        return 2
    result = tally(roots)
    if "--json" in argv:
        print(json.dumps(result, indent=2))
    else:
        show(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
