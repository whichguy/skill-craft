"""Write one blind judge input per (scenario, rep): the two arms' diffs as X and Y in a seeded random order.

    python3 -I judge_pack.py <scenarios dir> <arms dir> <out dir> <rep>

The key (which of X/Y is A) goes to <out dir>/key.json, never into a judge input.
"""

import json
import random
import subprocess
import sys
from pathlib import Path


def diff(tree: Path) -> str:
    run = lambda *a: subprocess.run(a, cwd=tree, capture_output=True, text=True).stdout
    run("git", "add", "-N", ".")          # untracked files show as additions
    text = run("git", "diff", "--no-color", "HEAD")
    run("git", "reset", "-q")
    return text


def result(arm: Path) -> str:
    p = arm / "run/inbox/result.md"
    notes = arm / "run/notes/document.md"
    return (p.read_text() if p.exists() else "(no result file)") + (
        "\n----- RUN/notes/document.md -----\n" + notes.read_text() if notes.exists() else "")


def main(scen_dir, arms_dir, out_dir, rep):
    scen = json.loads(Path(scen_dir, "scenarios.json").read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    key_path = out / "key.json"
    key = json.loads(key_path.read_text()) if key_path.exists() else {}
    rng = random.Random(f"docexp-{rep}")
    for name, sc in scen.items():
        a, b = Path(arms_dir, f"{name}-A-r{rep}"), Path(arms_dir, f"{name}-B-r{rep}")
        if not (a.exists() and b.exists()):
            continue
        pair = [("A", a), ("B", b)]
        rng.shuffle(pair)
        key[f"{name}-r{rep}"] = {"X": pair[0][0], "Y": pair[1][0]}
        request = Path(scen_dir, name, "run/request.md").read_text()
        body = [f"# Scenario {name}", "", "## Request", request, "## The step's state before the document stage",
                "Implement and test were done; the uncommitted change before documentation was: " + ", ".join(sc["changed"]),
                "Earlier results (implement summary, not-covered behaviour, test summary):"]
        for res in ("implement-S1.md", "test-S1.md"):
            body.append(Path(scen_dir, name, "run/results", res).read_text())
        body.append("## Reference checklist (what a strong document stage should catch; not exhaustive)")
        body.append(json.dumps(sc["planted"], indent=1))
        for label, (_, arm) in zip("XY", pair):
            body += [f"## Arm {label}: diff against the base commit (code, tests and docs)", "```diff", diff(arm / "worktree"),
                     "```", f"## Arm {label}: result and notes", result(arm)]
        (out / f"{name}-r{rep}.md").write_text("\n".join(body))
    key_path.write_text(json.dumps(key, indent=1))
    print(sorted(p.name for p in out.glob("*.md")))


if __name__ == "__main__":
    main(*sys.argv[1:5])
