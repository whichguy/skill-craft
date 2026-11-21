#!/usr/bin/env python3
"""What each review of a stage that arm L removes changed, as packets for two judges (round 7).

For every whole delivery among the given run folders and every Improve review of `spec`, `test-strategy`, `plan`,
`step-plan` or `system-test-author` in it:

  before   the tree ShipLoop snapshotted when the review was bound (run/improve/<action>-bind.md, key `tree`) and the
           result as submitted (run/improve/<action>-bind-result.json);
  after    the tree ShipLoop recorded after the review's last pass (run/improve/<action>/reviews/pass-<n>.json, key
           `tree`), when a pass says the tree changed, and the result as accepted (run/results/<action>.md), when a
           pass says the result changed.

A packet holds the reviewed stage, the request the delivery was built from, the tree diff (ShipLoop's own review
files left out) and the result diff (bookkeeping keys left out), the two diffs cut at 12,000 characters together:
in the tree diff the files come smallest first, each file's diff is cut at 2,500 characters, and a file that no longer
fits is named with its size, so one large file cannot hide the others. OUT/key.json says which run, driver and arm each
packet is; the judges get the packets only. A review that changed neither is counted in the key and gets no packet.

Usage: python3 -I removed_review_diffs.py OUT RUN_FOLDER [RUN_FOLDER ...]
"""
import difflib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import review_option_census as option

REMOVED = ("spec", "test-strategy", "plan", "step-plan", "system-test-author")
BOOKKEEPING = {"evidence_refs", "check_refs", "review_refs", "lessons", "no_commit", "headline", "summary"}
SKIP = (".shiploop-improve/", ".until-loop")
TREE_CAP, RESULT_CAP = 9000, 3000


def arm_of(name):
    found = re.search(r"-(S|L)-\d+$", name)
    return found.group(1) if found else "none asked" if "sol-medium" in name and "ticket-assignment" in name else "as shipped"


FILE_CAP = 2500


def cut(text, cap):
    return text if len(text) <= cap else text[:cap] + f"\n[... cut here: {len(text) - cap} more characters ...]\n"


def cut_tree(diff, cap):
    """A tree diff with every changed file visible: the files' diffs smallest first, each cut at FILE_CAP, and the
    files that no longer fit under ``cap`` listed by name and size."""
    chunks, current = [], []
    for line in diff.splitlines():
        if line.startswith("diff --git ") and current:
            chunks.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        chunks.append("\n".join(current))
    chunks.sort(key=len)
    shown, left, used = [], [], 0
    for chunk in chunks:
        name = chunk.splitlines()[0].split(" b/", 1)[-1]
        piece = cut(chunk, FILE_CAP)
        if used + len(piece) > cap and shown:
            left.append(f"{name} ({len(chunk)} characters of diff)")
            continue
        shown.append(piece)
        used += len(piece)
    tail = ("\n[... not shown, for length: " + "; ".join(left) + " ...]") if left else ""
    return "\n".join(shown) + tail


def tree_diff(worktree, before, after):
    if not before or not after or before == after:
        return ""
    out = base.git(worktree, "diff", "--no-renames", "--unified=2", before, after) or ""
    kept, keep = [], True
    for line in out.splitlines():
        if line.startswith("diff --git "):
            keep = not any(f" b/{prefix}" in line for prefix in SKIP)
        if keep:
            kept.append(line)
    return "\n".join(kept)


def result_diff(before, after):
    def plain(result):
        return json.dumps({k: v for k, v in (result or {}).items() if k not in BOOKKEEPING}, indent=1, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(plain(before), plain(after), "result as submitted", "result as accepted", lineterm="", n=1))


def main(out, folders):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    key, number = [], 0
    for folder in map(pathlib.Path, folders):
        for trace in sorted(folder.glob("**/.shiploop-runs/*/run/trace.jsonl")):
            run = trace.parent
            worktree = run.parent / "worktree"
            invocation = option.load(folder / "invocation.json")
            if invocation.get("kind") == "step-slice" or invocation.get("seeded"):
                continue
            try:
                request = (folder / "prompt.txt").read_text(errors="replace").strip()[:2500]
            except OSError:
                request = "(not recorded)"
            for bind in sorted((run / "improve").glob("*-bind.md"), key=lambda p: p.stat().st_mtime):
                action = bind.name[:-len("-bind.md")]
                record = base.state(run / "results" / f"{action}.md") or {}
                stage = record.get("stage")
                passes = run / "improve" / action / "passes.md"
                if stage not in REMOVED or not passes.exists():
                    continue
                before_tree = (base.state(bind) or {}).get("tree")
                recorded = [option.load(path) for path in sorted((run / "improve" / action / "reviews").glob("pass-*.json"),
                                                                 key=lambda path: int(path.stem.split("-")[1]))]
                recorded = [row for row in recorded if row]
                if not recorded:
                    continue
                tree = tree_diff(worktree, before_tree, recorded[-1].get("tree")) if any(row.get("changed") for row in recorded) else ""
                submitted = option.load(run / "improve" / f"{action}-bind-result.json")
                result = (result_diff(submitted, record.get("result") if isinstance(record.get("result"), dict) else {})
                          if submitted and any(row.get("result_changed") for row in recorded) else "")
                row = {"folder": folder.name, "case": invocation.get("case"), "driver": f"{invocation.get('model')} {invocation.get('effort')}",
                       "arm": arm_of(folder.name), "stage": stage, "action": action, "tree_chars": len(tree), "result_chars": len(result),
                       "packet": None}
                if tree or result:
                    number += 1
                    row["packet"] = number
                    (out / f"packet-{number:03d}.txt").write_text(
                        f"PACKET {number}\nReviewed stage: {stage}\n\n== The request the delivery was built from ==\n{request}\n\n"
                        "== What the review changed in the files ==\n"
                        + (cut_tree(tree, TREE_CAP) if tree else "(no file changed)") + "\n\n== What the review changed in the stage's recorded result ==\n"
                        + (cut(result, RESULT_CAP) if result else "(the result did not change)") + "\n")
                key.append(row)
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"reviews of the removed stages: {len(key)}; with a change, so with a packet: {number}")
    for row in key:
        print(f"  {row['folder']:<30}{row['driver']:<24}{row['stage']:<20}"
              f"{'packet ' + str(row['packet']) if row['packet'] else 'no change':<12} tree {row['tree_chars']:>6} chars, result {row['result_chars']:>5}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
