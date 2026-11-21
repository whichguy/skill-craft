"""Where the items that fail on a correct reference come from, by the Source line their own specification gave them.

usage: by_source.py OUT_JSON TEXT:NAME=RUN_DIR...
       by_source.py specs OUT_JSON TEXT:NAME=RUN_DIR...

A run here is a test-strength cell that `grade.py strength` has graded: RUN_DIR holds work/ratchet/spec.md, run.json
and strength.json. TEXT names the enrichment text the run used, so runs of one text are pooled. For every run and
every text it counts, over the clauses written and over the clauses that fail on the reference, how many carry each
kind of Source (request, implied, existing, choice, discovery), how many the plan stage added, and how many of each
kind make the product refuse or require something (a word match on the statement); it lists each failing item and
each choice clause so they can be read. It reads and never writes inside a run folder. Standard library only.

`specs` needs no grading: it reads each run's specification as its spec stage left it (the run's `spec` commit, so
clauses a later stage added are not counted) and counts what was written: clauses by Source, the refusals the
writer added on its own (choice or implied clauses the word match marks), and `Open:` lines.
"""
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ratchet  # the loop's own reader of a specification

KINDS = ("request", "implied", "existing", "choice", "discovery")
# A clause that is about the tests the request asks for, told by its statement: a rough mark, checked by reading.
ABOUT_TESTS = re.compile(r"node:test|npm test|test suite|tests? run|test command", re.IGNORECASE)
# A clause whose statement makes the product refuse, fail or require something, told by its words: a rough mark.
# The list was written once, after reading the clauses, and was not adjusted after its first run.
REFUSES = re.compile(r"\b(error|errors|invalid|refuse[sd]?|reject[s]?|prevent[s]?|must|throws?|raises?|unusable|cannot"
                     r"|fails?|exclude[s]?)\b", re.IGNORECASE)


def kind_of(source):
    """The first word of a Source line; anything unexpected is kept visible, not folded into a known kind."""
    word = re.match(r"[A-Za-z]+", source.strip())
    word = word.group(0).lower() if word else ""
    return word if word in KINDS else f"other:{word or '?'}"


def share(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else "-"


def table(written, failing):
    """Lines of one table: per kind, written, failing and the failing share of that kind; then what is not `existing`."""
    lines = []
    kinds = sorted(set(written) | set(failing), key=lambda kind: (KINDS.index(kind) if kind in KINDS else len(KINDS), kind))
    for kind in kinds:
        lines.append(f"   {kind:12s} written {written.get(kind, 0):4d}   failing {failing.get(kind, 0):3d}   "
                     f"({share(failing.get(kind, 0), written.get(kind, 0))} of its kind)")
    total, bad = sum(written.values()), sum(failing.values())
    new, new_bad = total - written.get("existing", 0), bad - failing.get("existing", 0)
    lines.append(f"   {'all':12s} written {total:4d}   failing {bad:3d}   ({share(bad, total)})")
    lines.append(f"   {'not existing':12s} written {new:4d}   failing {new_bad:3d}   ({share(new_bad, new)})")
    return lines


def read_run(folder):
    folder = Path(folder)
    items = ratchet.read_spec(folder / "work")
    strength = json.loads((folder / "strength.json").read_text())
    run = json.loads((folder / "run.json").read_text())
    failing = list(strength["clauses_failing_on_reference"]) + list(strength["use_cases_failing_on_reference"])
    plan_added = [ident for cycle in run.get("cycles", []) for ident in cycle.get("plan_added") or []]
    counts = {"written": {"clauses": Counter(), "use_cases": Counter()},
              "failing": {"clauses": Counter(), "use_cases": Counter()}}
    listing, choices = [], []
    refusing = {"written": Counter(), "failing": Counter()}  # clauses only, by kind, where the statement refuses
    for ident, item in items.items():
        group = "clauses" if ident.startswith("C-") else "use_cases"
        kind = kind_of(item["source"])
        counts["written"][group][kind] += 1
        refuses = group == "clauses" and bool(REFUSES.search(item["statement"]))
        if refuses:
            refusing["written"][kind] += 1
            refusing["failing"][kind] += ident in failing
        if group == "clauses" and kind == "choice":
            choices.append({"id": ident, "failing": ident in failing, "refuses": refuses,
                            "statement": item["statement"], "source": item["source"]})
        if ident in failing:
            counts["failing"][group][kind] += 1
            listing.append({"id": ident, "kind": kind, "plan_added": ident in plan_added, "refuses": refuses,
                            "statement": item["statement"], "source": item["source"]})
    request_failing = [entry["id"] for entry in listing if entry["kind"] == "request" and entry["id"].startswith("C-")]
    about_tests = [entry["id"] for entry in listing if entry["id"] in request_failing and ABOUT_TESTS.search(entry["statement"])]
    return {"case": strength["case"], "enrich": run.get("enrich", "single"), "counts": counts,
            "request_clauses_failing": request_failing, "request_clauses_about_tests": about_tests,
            "refusing": {side: dict(count) for side, count in refusing.items()}, "choice_clauses": choices,
            "plan_added": plan_added, "plan_added_failing": [ident for ident in plan_added if ident in failing],
            "failing_not_in_spec": [ident for ident in failing if ident not in items], "failing_items": listing}


def spec_as_written(folder):
    """The specification's items at the run's `spec` commit: what the spec stage wrote, before any other stage."""
    folder = Path(folder)
    run = json.loads((folder / "run.json").read_text())
    commits = [snap["commit"] for snap in run.get("snapshots", []) if snap["label"] == "spec"]
    if not commits:
        raise SystemExit(f"{folder}: run.json records no `spec` commit")
    text = subprocess.run(["git", "-C", str(folder / "work"), "show", f"{commits[0]}:ratchet/spec.md"],
                          check=True, capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory() as scratch:
        (Path(scratch) / "ratchet").mkdir()
        (Path(scratch) / "ratchet" / "spec.md").write_text(text)
        return run, ratchet.read_spec(scratch)


def specs(out_path, entries):
    """Count what each specification wrote, with no grading."""
    result, rows = {}, []
    for entry in entries:
        label, _, folder = entry.partition("=")
        run, items = spec_as_written(folder)
        kinds, added_refusals, opens = Counter(), [], []
        use_cases = sum(1 for ident in items if ident.startswith("U-"))
        for ident, item in items.items():
            if not ident.startswith("C-"):
                continue
            kind = kind_of(item["source"])
            kinds[kind] += 1
            if kind in ("choice", "implied") and REFUSES.search(item["statement"]):
                added_refusals.append({"id": ident, "kind": kind, "statement": item["statement"]})
            found = re.search(r"^Open: *(.+)$", item["block"], re.MULTILINE)
            if found:
                opens.append({"id": ident, "kind": kind, "statement": item["statement"], "open": found.group(1).strip()})
        seconds = sum(row["seconds"] for row in run.get("sessions", []) if row.get("role") == "spec")
        total = sum(kinds.values())
        result[label] = {"case": run.get("case"), "enrich": run.get("enrich", "single"), "clauses": total,
                         "use_cases": use_cases, "by_source": dict(kinds), "added_refusals": added_refusals,
                         "open_lines": opens, "spec_minutes": round(seconds / 60, 1)}
        rows.append((label, run.get("case"), total, use_cases, kinds, len(added_refusals), len(opens), seconds / 60))
    print(f"{'run':34s} {'clauses':>7s} {'use c.':>6s} {'request':>7s} {'implied':>7s} {'existing':>8s} {'choice':>6s} "
          f"{'added refusals':>14s} {'Open: lines':>11s} {'minutes':>7s}")
    for label, _case, total, use_cases, kinds, refusals, opens, minutes in rows:
        other = sum(count for kind, count in kinds.items() if kind not in KINDS)
        print(f"{label:34s} {total:7d} {use_cases:6d} {kinds.get('request', 0):7d} {kinds.get('implied', 0):7d} "
              f"{kinds.get('existing', 0):8d} {kinds.get('choice', 0):6d} {refusals:14d} {opens:11d} {minutes:7.1f}"
              + (f"   ({other} with an unexpected Source)" if other else ""))
    for label, row in result.items():
        if row["open_lines"]:
            print(f"\n== {label}: Open: lines")
            for entry in row["open_lines"]:
                print(f"   {entry['id']} [{entry['kind']}] {entry['statement']}\n        Open: {entry['open']}")
    Path(out_path).write_text(json.dumps(result, indent=1) + "\n")
    print(f"\nwrote {out_path}")


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    if sys.argv[1] == "specs":
        return specs(sys.argv[2], sys.argv[3:])
    out_path, entries = sys.argv[1], sys.argv[2:]
    result = {"runs": {}, "pooled": {}}
    pools = {}
    for entry in entries:
        label, _, folder = entry.partition("=")
        text = label.partition(":")[0]
        run = read_run(folder)
        result["runs"][label] = run
        pool = pools.setdefault(text, {"written": {"clauses": Counter(), "use_cases": Counter()},
                                       "failing": {"clauses": Counter(), "use_cases": Counter()},
                                       "plan_added": 0, "plan_added_failing": 0, "about_tests": 0, "runs": [],
                                       "refusing": {"written": Counter(), "failing": Counter()}})
        for side in ("written", "failing"):
            for group in ("clauses", "use_cases"):
                pool[side][group].update(run["counts"][side][group])
        pool["plan_added"] += len(run["plan_added"])
        pool["plan_added_failing"] += len(run["plan_added_failing"])
        pool["about_tests"] += len(run["request_clauses_about_tests"])
        for side in ("written", "failing"):
            pool["refusing"][side].update(run["refusing"][side])
        pool["runs"].append(label)
        written, failing = run["counts"]["written"], run["counts"]["failing"]
        print(f"== {label} ({run['case']}; run.json says enrich={run['enrich']}): "
              f"{sum(written['use_cases'].values())} use cases, {sum(failing['use_cases'].values())} fail on the reference; clauses:")
        print("\n".join(table(written["clauses"], failing["clauses"])))
        print(f"   the plan stage added {run['plan_added'] or 'nothing'}; of those failing: {run['plan_added_failing'] or 'none'}")
        print(f"   request-clauses-about-tests: of the request clauses failing {run['request_clauses_failing']}, "
              f"about the tests the request asks for: {run['request_clauses_about_tests'] or 'none'}")
        if run["failing_not_in_spec"]:
            print(f"   failing ids not found in the specification: {run['failing_not_in_spec']}")
    for text, pool in pools.items():
        print(f"\n#### pooled, text {text} ({len(pool['runs'])} runs): use cases written "
              f"{sum(pool['written']['use_cases'].values())}, failing {sum(pool['failing']['use_cases'].values())} "
              f"{dict(pool['failing']['use_cases'])}; clauses:")
        print("\n".join(table(pool["written"]["clauses"], pool["failing"]["clauses"])))
        print(f"   clauses the plan stage added: {pool['plan_added']}, failing on the reference: {pool['plan_added_failing']}")
        print(f"   request clauses failing that are about the tests the request asks for: {pool['about_tests']}")
        print("   clauses whose statement makes the product refuse or require something, against the rest of their kind:")
        for kind in KINDS:
            total, bad = pool["written"]["clauses"].get(kind, 0), pool["failing"]["clauses"].get(kind, 0)
            if not total:
                continue
            hard, hard_bad = pool["refusing"]["written"].get(kind, 0), pool["refusing"]["failing"].get(kind, 0)
            print(f"      {kind:10s} refuses: written {hard:3d}, failing {hard_bad:3d} ({share(hard_bad, hard)});   "
                  f"rest: written {total - hard:3d}, failing {bad - hard_bad:3d} ({share(bad - hard_bad, total - hard)})")
        result["pooled"][text] = {"runs": pool["runs"], "plan_added": pool["plan_added"],
                                  "plan_added_failing": pool["plan_added_failing"],
                                  "request_clauses_about_tests": pool["about_tests"],
                                  "refusing": {side: dict(count) for side, count in pool["refusing"].items()},
                                  "written": {group: dict(count) for group, count in pool["written"].items()},
                                  "failing": {group: dict(count) for group, count in pool["failing"].items()}}
    for run in result["runs"].values():
        run["counts"] = {side: {group: dict(count) for group, count in groups.items()}
                         for side, groups in run["counts"].items()}
    Path(out_path).write_text(json.dumps(result, indent=1) + "\n")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
