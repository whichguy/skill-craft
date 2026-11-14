#!/usr/bin/env python3
"""Reconstruct a late send-back as a stage-suite scenario at step-plan (the step-boundary replay's Q1).

Reads a retained run (its accepted results and its worktree's Git history) and writes
``test/shiploop_e2e/stage_cases/step-plan/<id>/``:
- ``repo/``: the tree at ``start_commit`` (the moment the item's first step began), so the knowledge home is the
  boundary's, not the neutral seed home (Astra's review: the neutral home is insufficient for a historical replay);
- ``route/<n>-<stage>/``: each done step's committed change, split by kind and laid before the stage that wrote it
  (code at implement, tests at test, documentation at document), then the interrupted step's draft;
- ``scenario.json``: ``seed_route`` with the run's own accepted results (``evidence_refs`` emptied: the old run's
  absolute paths would leak hindsight), ending with the recorded send-back;
- ``oracle/expected.json``: the done rows the amendment must keep, and the case's registered correction predicate.

Usage: reconstruct.py MANIFEST.json REPO_ROOT. The manifest's keys are documented in the replay's README.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DOC = re.compile(r"(^|/)(README[^/]*|CHANGELOG[^/]*)$|^docs/|\.md$")
TEST = re.compile(r"(^|/)(test|tests|__tests__|spec)/|\.(test|spec)\.[A-Za-z0-9]+$")


def block(path: Path) -> dict:
    text = path.read_text(errors="replace")
    found = re.search(r"```shiploop-state\n(.*?)\n```", text, re.S)
    if not found:
        raise SystemExit(f"{path}: no shiploop-state block")
    return json.loads(found.group(1))


def result(run: Path, action: str) -> dict:
    """The accepted result of ``action``, with evidence_refs emptied."""
    record = block(run / "results" / (action + ".md"))
    out = dict(record["result"])
    if "evidence_refs" in out:
        out["evidence_refs"] = []
    return out


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True, text=True).stdout


def kind(path: str) -> str:
    return "test" if TEST.search(path) else "document" if DOC.search(path) else "implement"


def export(tree: Path, commit: str, paths: list, dest: Path) -> None:
    for path in paths:
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(["git", "-C", str(tree), "show", f"{commit}:{path}"], check=True,
                                          capture_output=True).stdout)


def seed_records(run: Path, manifest: dict) -> dict:
    """The planning stages' real fields (``seed_from``: stage -> action), merged into the seed's synthetic results: what
    the step-plan packet and its gates read from them (spec primary, test layers and targets, plan assumptions)."""
    records = {}
    for stage, action in (manifest.get("seed_from") or {}).items():
        fields = {key: value for key, value in result(run, action).items()
                  if key not in ("outcome", "summary", "headline", "evidence_refs", "work_items")}
        if fields:
            records[stage] = fields
    return records


def main(manifest_path: str, repo_root: str) -> None:
    manifest = json.loads(Path(manifest_path).read_text())
    run, tree = Path(manifest["run"]), Path(manifest["worktree"])
    out = Path(repo_root) / "test/shiploop_e2e/stage_cases/step-plan" / manifest["id"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    start = manifest["start_commit"]
    files = [line for line in git(tree, "ls-tree", "-r", "--name-only", start).splitlines()
             if not line.startswith(".shiploop")]
    export(tree, start, files, out / "repo")
    route = [{"stage": "step-plan", "result": result(run, manifest["plan"])},
             {"stage": "test-spec", "result": result(run, manifest["test_spec"])}]
    if manifest.get("validate_existing"):
        route.append({"stage": "validate-existing", "result": result(run, manifest["validate_existing"])})
    for number, step in enumerate(manifest["done_steps"], 1):
        changed = [line for line in git(tree, "diff", "--name-only", f"{step['commit']}^", step["commit"]).splitlines()]
        missing = [line for line in changed if not git(tree, "ls-tree", step["commit"], "--", line).strip()]
        if missing:
            raise SystemExit(f"step {number} deletes {missing}: overlays are additive; reconstruct by hand")
        for stage in ("implement", "test", "document"):
            mine = [path for path in changed if kind(path) == stage]
            entry = {"stage": stage, "result": result(run, step[stage])}
            if mine:
                folder = f"route/{number}-{stage}"
                export(tree, step["commit"], mine, out / folder)
                entry["overlay"] = folder
            route.append(entry)
    interrupted = manifest["interrupted"]
    draft = interrupted.get("draft")
    folder = None
    if draft:
        folder = f"route/{len(manifest['done_steps']) + 1}-draft"
        export(tree, draft["commit"], draft["paths"], out / folder)
    for entry in interrupted["entries"]:   # the interrupted step's accepted stages, then the send-back
        row = {"stage": entry["stage"], "result": result(run, entry["action"])}
        if folder and entry.get("draft"):
            row["overlay"] = folder
        route.append(row)
    plan = block(run / "results" / (manifest["plan"] + ".md"))["result"]
    done = len(manifest["done_steps"])
    expected = {"done_rows": [{**row, "done": True} for row in plan["steps"][:done]],
                "correction": manifest["correction"]}
    (out / "oracle").mkdir()
    (out / "oracle" / "expected.json").write_text(json.dumps(expected, indent=1) + "\n")
    shutil.copy(Path(__file__).with_name("q1_oracle.py"), out / "oracle" / "q1_oracle.py")
    scenario = {
        "stage": "step-plan",
        "about": manifest["about"],
        "tags": ["replay", "fix-forward"],
        "tiers": ["render", "live"],
        "fixture": manifest["fixture"],
        **({"request_from": manifest["request_from"]} if "request_from" in manifest else {"request": manifest["request"]}),
        "options": {"delegation": "inline", "seed_home": False},
        "seed_records": seed_records(run, manifest),
        "seed_route": route,
        "planted": [{"id": "P1", "what": "Steps " + ", ".join(row["id"] for row in plan["steps"][:done])
                     + " are done; the amendment keeps them exactly", "signature": "Fix forward:"},
                    {"id": "P2", "what": manifest["fault"]}],
        "render": [{"proves": "P1", "packet_contains": "Fix forward: " + plan["steps"][0]["id"]}],
        "oracle": [{"proves": "P1", "outcome": ["done"]},
                   {"proves": "P1", "command": 'python3 "$STAGE_ORACLE/q1_oracle.py" fidelity', "exit": 0},
                   {"proves": "P2", "command": 'python3 "$STAGE_ORACLE/q1_oracle.py" correction', "exit": 0}],
        "live": {"samples": 4, "pass": 1},
    }
    (out / "scenario.json").write_text(json.dumps(scenario, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
