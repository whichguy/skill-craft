"""Where the items that fail on a correct reference come from, by the Source line their own specification gave them.

usage: by_source.py OUT_JSON TEXT:NAME=RUN_DIR...

A run here is a test-strength cell that `grade.py strength` has graded: RUN_DIR holds work/ratchet/spec.md, run.json
and strength.json. TEXT names the enrichment text the run used, so runs of one text are pooled. For every run and
every text it counts, over the clauses written and over the clauses that fail on the reference, how many carry each
kind of Source (request, implied, existing, choice, discovery), how many the plan stage added, and lists each
failing item so it can be read. It reads and never writes inside a run folder. Standard library only.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ratchet  # the loop's own reader of a specification

KINDS = ("request", "implied", "existing", "choice", "discovery")
# A clause that is about the tests the request asks for, told by its statement: a rough mark, checked by reading.
ABOUT_TESTS = re.compile(r"node:test|npm test|test suite|tests? run|test command", re.IGNORECASE)


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
    listing = []
    for ident, item in items.items():
        group = "clauses" if ident.startswith("C-") else "use_cases"
        kind = kind_of(item["source"])
        counts["written"][group][kind] += 1
        if ident in failing:
            counts["failing"][group][kind] += 1
            listing.append({"id": ident, "kind": kind, "plan_added": ident in plan_added,
                            "statement": item["statement"], "source": item["source"]})
    request_failing = [entry["id"] for entry in listing if entry["kind"] == "request" and entry["id"].startswith("C-")]
    about_tests = [entry["id"] for entry in listing if entry["id"] in request_failing and ABOUT_TESTS.search(entry["statement"])]
    return {"case": strength["case"], "enrich": run.get("enrich", "single"), "counts": counts,
            "request_clauses_failing": request_failing, "request_clauses_about_tests": about_tests,
            "plan_added": plan_added, "plan_added_failing": [ident for ident in plan_added if ident in failing],
            "failing_not_in_spec": [ident for ident in failing if ident not in items], "failing_items": listing}


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
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
                                       "plan_added": 0, "plan_added_failing": 0, "about_tests": 0, "runs": []})
        for side in ("written", "failing"):
            for group in ("clauses", "use_cases"):
                pool[side][group].update(run["counts"][side][group])
        pool["plan_added"] += len(run["plan_added"])
        pool["plan_added_failing"] += len(run["plan_added_failing"])
        pool["about_tests"] += len(run["request_clauses_about_tests"])
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
        result["pooled"][text] = {"runs": pool["runs"], "plan_added": pool["plan_added"],
                                  "plan_added_failing": pool["plan_added_failing"],
                                  "request_clauses_about_tests": pool["about_tests"],
                                  "written": {group: dict(count) for group, count in pool["written"].items()},
                                  "failing": {group: dict(count) for group, count in pool["failing"].items()}}
    for run in result["runs"].values():
        run["counts"] = {side: {group: dict(count) for group, count in groups.items()}
                         for side, groups in run["counts"].items()}
    Path(out_path).write_text(json.dumps(result, indent=1) + "\n")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
