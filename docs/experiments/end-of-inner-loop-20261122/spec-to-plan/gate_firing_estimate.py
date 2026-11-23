#!/usr/bin/env python3
"""Read-only estimate: how often would a "changed requirement after the plan" gate fire on saved deliveries?

The candidate rule (README section 4): a requirement R-<n> counts as changed after the plan when its entry in
docs/shiploop/spec.md, as the plan boundary commit held it, has a line that a later commit no longer holds in that
entry (a line added to an entry is no change: the rule of shiploop_defaults.changed), or when the entry is new or newly
retired after the boundary.  Lines a step or carry-forward added after the boundary may be rewritten freely.

For each saved run of ShipLoop >= 2.4 with a plan boundary (scan_spec_after_plan.json), walk its post-plan commits
that touched spec.md and record the first commit (and its stage) at which each R-<n> became changed under this rule.
Parsing uses ShipLoop's own entry reader (shiploop_knowledge_home._entries) from the skill-craft checkout in argv[2].
Runs only `git show`; prints a summary and writes per-run rows to argv[3].  Usage:
    python3 gate_firing_estimate.py scan_spec_after_plan.json /Users/dadleet/src/skill-craft gate_firing_estimate.json
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

SPEC = "docs/shiploop/spec.md"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_removed_lines import minor  # noqa: E402
from engine_split import engine  # noqa: E402


def show(repo, commit):
    done = subprocess.run(["git", "-C", repo, "show", commit + ":" + SPEC], capture_output=True, text=True,
                          errors="replace")
    return done.stdout if done.returncode == 0 else ""


def lines(text):
    return {" ".join(line.split()) for line in text.splitlines() if line.strip()}


def changed(base, now):
    """R-<n> changed from ``base`` to ``now`` (entries maps): a base line gone, a new ID, or newly retired."""
    found = {}
    for ident, entry in now.items():
        if ident not in base:
            found[ident] = "new"
        elif entry.retired and not base[ident].retired:
            found[ident] = "retired"
        elif not lines(base[ident].text) <= lines(entry.text):
            found[ident] = "rewritten"
    for ident in base:
        if ident not in now:
            found[ident] = "dropped"
    return found


def main():
    rows = json.load(open(sys.argv[1]))
    checkout = Path(sys.argv[2])
    sys.path.insert(0, str(checkout / "skills/shiploop/scripts"))
    import shiploop_knowledge_home as knowledge  # noqa: E402

    out = []
    for row in rows:
        if not row.get("has_boundary") or minor(row.get("shiploop")) < (2, 4):
            continue
        repo = row["folder"] + "/work"
        log = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=%H%x09%s"], capture_output=True,
                             text=True, errors="replace").stdout.splitlines()
        commits = [line.split("\t", 1) for line in log if "\t" in line]
        post = {commit["commit"] for commit in row["post_plan"]}
        first_post = next((index for index, (sha, _) in enumerate(commits) if sha in post), None)
        if first_post is None:
            out.append({"folder": row["folder"], "engine": engine(row["folder"], str(checkout)), "fired": {}})
            continue
        base_sha = commits[first_post - 1][0] if first_post > 0 else None
        base = knowledge._entries(show(repo, base_sha), "R") if base_sha else {}
        fired = {}
        for commit in row["post_plan"]:
            now = knowledge._entries(show(repo, commit["commit"]), "R")
            for ident, how in changed(base, now).items():
                fired.setdefault(ident, {"how": how, "stage": commit["stage"], "commit": commit["commit"][:12],
                                         "subject": commit["subject"][:100]})
        out.append({"folder": row["folder"], "engine": engine(row["folder"], str(checkout)), "fired": fired})
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1) + "\n")
    for name in ("main", "candidate"):
        group = [entry for entry in out if entry["engine"] == name]
        fired_runs = [entry for entry in group if entry["fired"]]
        by_stage = Counter(stage for entry in fired_runs for stage in {f["stage"] for f in entry["fired"].values()})
        how = Counter(f["how"] for entry in fired_runs for f in entry["fired"].values())
        print(name, "runs (ShipLoop >= 2.4, with a plan boundary):", len(group), "| the rule fires in:", len(fired_runs))
        print("   first stage that changed a requirement, per run:", dict(by_stage))
        print("   kinds of change, per requirement:", dict(how))
        for entry in fired_runs:
            print("   ", entry["folder"].replace(str(Path.home()) + "/", "~/"), {ident: (f["stage"], f["how"])
                                                                           for ident, f in entry["fired"].items()})


if __name__ == "__main__":
    main()
