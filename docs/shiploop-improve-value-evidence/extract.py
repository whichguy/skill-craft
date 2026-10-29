"""Extract ShipLoop Improve review rows from E2E run folders (read-only).

Usage:  python3 -I extract.py [--out DIR] [RUN_PARENT ...]

Every Improve child of a ShipLoop run lives in
    <run>/.shiploop-runs/<name>/worktree/.shiploop-improve/<stage>-<8 hex>/
with one `reviews/pass-<n>.json` + `reviews/review-<n>.md` per pass. This script
joins those with the run's own records and writes three JSON files:

    runs.json      one row per run: model, versions, wall seconds, plan size
    reviews.json   one row per Improve child: stage, work item, pass count, seconds
    passes.json    one row per pass: label, files changed (git tree diff), findings
    review-text.json  the Found / Changed / Class text of every pass that is non-trivial
                   or edited something (the input to the finding-level labelling)

Method for "what did a pass change" (no trust in the `commit` field, which is
null for many edited passes):

  * `pass-<n>.json` carries `tree`, the git tree hash of the worktree after the
    pass. The first pass is diffed against the tree in
    `run/improve/<nav-id>-bind.md` (the snapshot taken when the child started),
    later passes against the previous pass's tree. `git diff-tree` names the files.
  * `result_changed` says the accepted stage result (a file outside the tree, in
    `run/inbox/`) was edited: a run record, not a product file.
  * Each file is bucketed: record (docs/shiploop/**), test, doc (other markdown
    and docs/), code (everything else, config included).

The script never writes inside a run folder.
"""
import argparse
import json
import os
import re
import subprocess
import sys

DEFAULT_PARENTS = [
    "/Users/dadleet/e2e-runs/20261020",
    "/Users/dadleet/e2e-runs/20261024",
    "/Users/dadleet/e2e-runs/20261025",
    "/Users/dadleet/e2e-runs/20261026",
    "/Users/dadleet/e2e-runs/20261027",
    "/Users/dadleet/e2e-runs/20261028",
    "/Users/dadleet/e2e-runs-owner-note/20261028",
]
SKIP_FRAGMENTS = ("/seed/", "/evidence/", "/slice")  # slices, seeds and audit copies are not full runs
STATE_RE = re.compile(r"```shiploop-state\n(.*?)\n```", re.DOTALL)
CHILD_RE = re.compile(r"^(?P<stage>.+)-(?P<suffix>[0-9a-f]{8})$")
TEST_DIRS = {"test", "tests", "test-support", "__tests__", "spec", "specs"}
TEST_NAME_RE = re.compile(
    r"(^test_.*|.*_test\.[A-Za-z]+$|.*\.test\.[A-Za-z]+$|.*\.spec\.[A-Za-z]+$|.*Test\.(cls|trigger)$)"
)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def bucket(path):
    parts = path.split("/")
    base = parts[-1]
    if path.startswith("docs/shiploop/") or path.startswith(".shiploop"):
        return "record"
    if any(part in TEST_DIRS for part in parts[:-1]) or TEST_NAME_RE.match(base):
        return "test"
    if path.startswith("docs/") or base.lower().endswith(".md"):
        return "doc"
    return "code"


def find_worktrees(parent):
    """Yield (run_root, shiploop_run_dir) for every full run under parent."""
    for dirpath, dirnames, _ in os.walk(parent):
        if dirpath.endswith("/.shiploop-runs"):
            dirnames[:] = []
            run_root = os.path.dirname(dirpath)
            for name in sorted(os.listdir(dirpath)):
                full = os.path.join(dirpath, name)
                if any(frag in full + "/" for frag in SKIP_FRAGMENTS):
                    continue
                if os.path.isdir(os.path.join(full, "worktree", ".shiploop-improve")):
                    yield run_root, full
        elif any(frag in dirpath + "/" for frag in SKIP_FRAGMENTS) or "/.git" in dirpath:
            dirnames[:] = []


def run_state(run_dir):
    path = os.path.join(run_dir, "run", "state.md")
    if not os.path.exists(path):
        return None
    match = STATE_RE.search(read(path))
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def plan_size(state):
    """Work items and steps, from the run's final state record."""
    if not state:
        return {}
    accepted = state.get("accepted", {})
    history = {entry["action"]: entry for entry in state.get("history", []) if "action" in entry}
    planned, added = None, 0
    for action, result in accepted.items():
        stage = history.get(action, {}).get("stage")
        items = [w.get("id") if isinstance(w, dict) else w for w in result.get("work_items", [])]
        if stage == "plan" and items:
            planned = len(items)
        if result.get("outcome") == "add-work":
            added += len(items)
    steps = {}
    for action, result in accepted.items():
        entry = history.get(action, {})
        if entry.get("stage") == "step-plan" and isinstance(result.get("steps"), list):
            steps.setdefault(entry.get("workitem"), []).append(len(result["steps"]))
    final_items = [w.get("id") for w in state.get("work_items", [])]
    return {
        "items_planned": planned,  # None when the run never accepted a plan (the state then holds one placeholder item)
        "items_added_after_plan": added,
        "items_final": len(final_items) if final_items else None,
        "steps_first_plan": sum(v[0] for v in steps.values()) if steps else None,
        "steps_last_plan": sum(v[-1] for v in steps.values()) if steps else None,
        "steps_by_item": {k: v for k, v in steps.items() if k},
        "stage_final": state.get("stage"),
    }


def run_meta(run_root):
    result = load_json(os.path.join(run_root, "result.json")) or {}
    versions = result.get("versions") or {}
    span = result.get("span") or {}
    return {
        "case": result.get("case"),
        "host": result.get("host"),
        "backend": result.get("backend"),
        "model": result.get("model"),
        "effort": result.get("effort"),
        "passed": result.get("pass"),
        "plugin_version": versions.get("plugin_version"),
        "shiploop_version": versions.get("shiploop_version"),
        "wall_seconds": round(span["ended"] - span["started"]) if span.get("ended") and span.get("started") else None,
    }


def run_metrics(run_root):
    """Stage seconds and per-child review seconds from the run's metrics.json, where present."""
    metrics = load_json(os.path.join(run_root, "metrics.json")) or {}
    stages = metrics.get("stages") if isinstance(metrics.get("stages"), list) else []
    per_child = (metrics.get("improve_reviews") or {}).get("per_child") or []
    return {
        "active_seconds": round(sum(st.get("seconds") or 0 for st in stages), 1) if stages else None,
        "stage_seconds": {st["stage"]: st.get("seconds") for st in stages if "stage" in st} if stages else None,
        "review_seconds": {c["child"]: c.get("review_seconds") for c in per_child if "child" in c},
    }


def passes_table(run_dir, nav_id):
    """Per-pass seconds from run/improve/<nav-id>/passes.md, keyed by pass number."""
    path = os.path.join(run_dir, "run", "improve", nav_id, "passes.md")
    seconds = {}
    if not os.path.exists(path):
        return seconds
    header = None
    for line in read(path).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] == "stage":
            header = cells
        elif header and len(cells) == len(header) and cells[1].isdigit() and "seconds" in header:
            value = cells[header.index("seconds")]
            if value.isdigit():
                seconds[int(cells[1])] = int(value)
    return seconds


def bind_tree(run_dir, nav_id):
    path = os.path.join(run_dir, "run", "improve", nav_id + "-bind.md")
    if not os.path.exists(path):
        return None
    match = STATE_RE.search(read(path))
    if not match:
        return None
    try:
        return json.loads(match.group(1)).get("tree")
    except ValueError:
        return None


def tree_files(worktree, before, after):
    if not before or not after:
        return None, "no baseline tree" if not before else "no pass tree"
    if before == after:
        return [], None
    done = subprocess.run(
        ["git", "-C", worktree, "diff-tree", "-r", "--name-only", before, after],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        return None, done.stderr.strip()[:160]
    return [line for line in done.stdout.splitlines() if line], None


def section(text, name, following):
    """Text of `name:` up to the next of `following:` at line start."""
    stops = "|".join(re.escape(f) for f in following)
    match = re.search(r"^%s:\s*(.*?)(?=^(?:%s):|^## |\Z)" % (re.escape(name), stops), text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""


# Passes recorded before the `edited` / `result_changed` fields existed note a
# corrected stage result (a file outside the tree) only in their Changed text.
OLD_RESULT_EDIT = re.compile(r"final[-_ ]result|stage result|result record|no (repository|tracked) file|inbox/", re.IGNORECASE)

NUM_PAREN = re.compile(r"(?:^|(?<=[\s;:.]))\((\d{1,2})\)\s")
NUM_LINE = re.compile(r"^\s*(\d{1,2})[.)]\s+", re.MULTILINE)
NOTHING = re.compile(r"nothing (material|to change)|no (material|defect|finding)|none\b", re.IGNORECASE)


def split_findings(found):
    """Split a `Found:` section into numbered findings; method says how."""
    if not found:
        return [], "empty"
    best = []
    for regex, method in ((NUM_PAREN, "paren"), (NUM_LINE, "line")):
        marks = [(m.start(), int(m.group(1)), m.end()) for m in regex.finditer(found)]
        seq, expect = [], 1
        for start, number, end in marks:
            if number == expect:
                seq.append((start, end))
                expect += 1
        if len(seq) > len(best):
            best, best_method = seq, method
    if best:
        pieces = []
        for index, (_, end) in enumerate(best):
            stop = best[index + 1][0] if index + 1 < len(best) else len(found)
            pieces.append(found[end:stop].strip())
        return pieces, best_method
    if NOTHING.search(found[:200]) and len(found) < 400:
        return [], "none-stated"
    return [found], "unnumbered"


def parse_review(path):
    text = read(path)
    front = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    meta = {}
    if front:
        for line in front.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        text = text[front.end():]
    order = ["Read", "Found", "Changed", "Checked", "Class"]
    found = section(text, "Found", order)
    changed = section(text, "Changed", order)
    klass = section(text, "Class", order + ["Handoff"])
    pieces, method = split_findings(found)
    return meta, found, changed, klass, pieces, method


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", nargs="*", default=DEFAULT_PARENTS)
    parser.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()

    runs, reviews, passes, texts = [], [], [], []
    for parent in args.parents:
        for run_root, run_dir in find_worktrees(parent):
            worktree = os.path.join(run_dir, "worktree")
            improve_dir = os.path.join(worktree, ".shiploop-improve")
            state = run_state(run_dir)
            history = {e["action"]: e for e in (state or {}).get("history", []) if "action" in e}
            by_suffix = {action[-8:]: action for action in (state or {}).get("improve_results", {})}
            run_id = os.path.relpath(run_root, "/Users/dadleet")
            meta = run_meta(run_root)
            size = plan_size(state)
            timing = run_metrics(run_root)
            children = []
            for name in sorted(os.listdir(improve_dir)):
                m = CHILD_RE.match(name)
                if not m or not os.path.isdir(os.path.join(improve_dir, name, "reviews")):
                    continue
                children.append((name, m.group("stage"), m.group("suffix")))
            if not children:
                continue
            run_row = dict(run=run_id, run_dir=os.path.relpath(run_dir, "/Users/dadleet"), **meta, **size,
                           active_seconds=timing["active_seconds"], stage_seconds=timing["stage_seconds"])
            for name, stage, suffix in children:
                nav_id = by_suffix.get(suffix)
                seconds = passes_table(run_dir, nav_id) if nav_id else {}
                prev_tree = bind_tree(run_dir, nav_id) if nav_id else None
                item = history.get(nav_id, {}).get("workitem") if nav_id else None
                pass_files = sorted(
                    f for f in os.listdir(os.path.join(improve_dir, name, "reviews")) if re.match(r"pass-\d+\.json$", f)
                )
                child_pass_rows = []
                for pass_file in sorted(pass_files, key=lambda f: int(re.findall(r"\d+", f)[0])):
                    number = int(re.findall(r"\d+", pass_file)[0])
                    pass_json = load_json(os.path.join(improve_dir, name, "reviews", pass_file)) or {}
                    review_path = os.path.join(improve_dir, name, "reviews", "review-%d.md" % number)
                    meta_md, found, changed, klass, pieces, method = (
                        parse_review(review_path) if os.path.exists(review_path) else ({}, "", "", "", [], "missing")
                    )
                    files, error = tree_files(worktree, prev_tree, pass_json.get("tree"))
                    buckets = sorted({bucket(f) for f in files}) if files else []
                    old_format = "edited" not in pass_json
                    result_changed = bool(pass_json.get("result_changed"))
                    if old_format and not files and pass_json.get("label") == "non-trivial" and OLD_RESULT_EDIT.search(changed):
                        result_changed = True  # inferred from the Changed text, not recorded
                    product = any(b in ("code", "test") for b in buckets)
                    if not pass_json.get("edited") and not files and not result_changed:
                        # a non-trivial pass that left no trace in the tree or the recorded result: the fix lives
                        # in a run note or scratch script (old format) or was not made
                        outcome = "unrecorded" if pass_json.get("label") == "non-trivial" else "none"
                    elif product:
                        outcome = "product"
                    elif "doc" in buckets:
                        outcome = "doc"
                    elif "record" in buckets:
                        outcome = "record"
                    elif result_changed:
                        outcome = "run-result"
                    else:
                        outcome = "unknown"
                    row = {
                        "run": run_id,
                        "child": name,
                        "stage": stage,
                        "workitem": item,
                        "pass": number,
                        "label": pass_json.get("label") or meta_md.get("classification"),
                        "format": "old" if old_format else "new",
                        "result_changed_inferred": old_format and result_changed and not pass_json.get("result_changed"),
                        "edited": pass_json.get("edited"),
                        "tree_changed": pass_json.get("changed"),
                        "result_changed": result_changed,
                        "lines": pass_json.get("lines"),
                        "seconds": seconds.get(number),
                        "at": pass_json.get("at"),
                        "files": files,
                        "buckets": buckets,
                        "outcome": outcome,
                        "tree_error": error,
                        "numbered_findings": len(pieces),
                        "numbering": method,
                        "class_text": klass[:300],
                    }
                    passes.append(row)
                    child_pass_rows.append(row)
                    if row["label"] == "non-trivial" or outcome != "none":
                        texts.append({
                            "id": "%s|%s|%d" % (run_id, name, number), "stage": stage, "label": row["label"],
                            "buckets": buckets, "result_changed": result_changed, "files": files,
                            "found": found, "changed": changed, "class": klass,
                        })
                    prev_tree = pass_json.get("tree") or prev_tree
                reviews.append({
                    "run": run_id, "child": name, "stage": stage, "workitem": item, "nav_id": nav_id,
                    "passes": len(child_pass_rows),
                    "review_seconds": timing["review_seconds"].get(name),
                    "non_trivial_passes": sum(1 for r in child_pass_rows if r["label"] == "non-trivial"),
                    "seconds": sum(r["seconds"] or 0 for r in child_pass_rows) if all(r["seconds"] is not None for r in child_pass_rows) else None,
                    "product_passes": sum(1 for r in child_pass_rows if r["outcome"] == "product"),
                })
            run_row["improve_children"] = len([r for r in reviews if r["run"] == run_id])
            run_row["improve_seconds"] = sum(r["seconds"] or 0 for r in reviews if r["run"] == run_id)
            run_row["improve_review_seconds"] = round(sum(r["review_seconds"] or 0 for r in reviews if r["run"] == run_id), 1)
            runs.append(run_row)

    os.makedirs(args.out, exist_ok=True)
    for name, rows in (("runs", runs), ("reviews", reviews), ("passes", passes), ("review-text", texts)):
        with open(os.path.join(args.out, name + ".json"), "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=1, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
    print("runs=%d reviews=%d passes=%d texts=%d" % (len(runs), len(reviews), len(passes), len(texts)))


if __name__ == "__main__":
    sys.exit(main())
