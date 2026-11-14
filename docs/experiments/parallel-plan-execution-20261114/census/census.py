"""Step-plan parallelism census (2026-11-14): how much parallelism do the recorded step plans' `deps` expose?

Offline and read-only: reads recorded ShipLoop E2E runs, never calls a model or a ShipLoop command. Stdlib only and
deterministic (sorted traversal, sorted output). Method, definitions and limits: README.md beside this file.

    python3 -I census.py [ROOT ...]     # default roots: every /Users/dadleet/e2e-runs* folder
                                        # writes evidence/census.json and prints a summary

Enumeration follows docs/experiments/concern-scope-20261114/concern_scope.py (results/*.md, the shiploop-state block,
state.md for the request, one row per action id); it is re-implemented here, not imported.
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
PREFIXES = ("$skill-craft:shiploop ",)
GLOB_CHARS = re.compile(r"[*?\[{]")


def state_block(path: pathlib.Path):
    try:
        match = BLOCK.search(path.read_text(encoding="utf-8", errors="replace"))
        return json.loads(match.group(1)) if match else None
    except (OSError, json.JSONDecodeError):
        return None


def normalise(request: str) -> str:
    text = request.strip()
    for prefix in PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.strip()


# ---------------------------------------------------------------- shape

def shape(steps):
    """Levels, width, independent pairs and class of one step list (list order is a topological order)."""
    n = len(steps)
    ids = [str(step.get("id")) for step in steps]
    has_deps = [isinstance(step.get("deps"), list) for step in steps]
    out = {"n": n, "deps_on": "every" if all(has_deps) else ("none" if not any(has_deps) else "some")}
    if n == 0:
        out["class"] = "empty"
        return out
    if not all(has_deps):
        out["class"] = "unknown"
        return out
    position = {sid: i for i, sid in enumerate(ids)}
    bad = [(ids[i], d) for i, step in enumerate(steps) for d in step["deps"] if position.get(str(d), n) >= i]
    out["bad_deps"] = len(bad)
    level, ancestors = [], []
    for i, step in enumerate(steps):
        deps = [position[str(d)] for d in step["deps"] if position.get(str(d), n) < i]
        level.append(1 + max((level[d] for d in deps), default=0))
        anc = set(deps)
        for d in deps:
            anc |= ancestors[d]
        ancestors.append(anc)
    L = max(level)
    width = collections.Counter(level)
    pairs = n * (n - 1) // 2
    indep = [(i, j) for j in range(n) for i in range(j) if i not in ancestors[j]]
    chain = all([str(d) for d in steps[i]["deps"]] == [ids[i - 1]] for i in range(1, n))
    if n == 1:
        cls = "single-step"
    elif all(not step["deps"] for step in steps):
        cls = "all-independent"
    elif chain:
        cls = "chain"
    elif not indep:
        cls = "ordered-non-chain"
    else:
        cls = "mixed"
    out.update({"L": L, "W": max(width.values()), "level": level, "pairs": pairs, "independent_pairs": len(indep),
                "class": cls, "S_levels": n / L, "_ancestors": ancestors, "_indep": indep})
    return out


# ---------------------------------------------------------------- write sets

def norm_path(path: str) -> str:
    path = str(path).strip()
    while path.startswith("./"):
        path = path[2:]
    cut = GLOB_CHARS.search(path)
    if cut:  # a glob: compare its fixed directory prefix
        path = path[:cut.start()].rsplit("/", 1)[0] + "/" if "/" in path[:cut.start()] else ""
    return path.rstrip("/")


def overlaps(a, b) -> bool:
    for x in a:
        for y in b:
            if x == "" or y == "" or x == y or x.startswith(y + "/") or y.startswith(x + "/"):
                return True
    return False


def conflicts(steps, pairs):
    counts = collections.Counter()
    sets = [[norm_path(p) for p in (step.get("paths") or []) if str(p).strip()] for step in steps]
    for i, j in pairs:
        if not sets[i] or not sets[j]:
            counts["no_paths"] += 1
        elif overlaps(sets[i], sets[j]):
            counts["overlap"] += 1
        else:
            counts["disjoint"] += 1
    return {"pairs": len(pairs), "overlap": counts["overlap"], "disjoint": counts["disjoint"],
            "no_paths": counts["no_paths"]}


# ---------------------------------------------------------------- durations

def load_trace(run: pathlib.Path):
    path = run / "trace.jsonl"
    if not path.is_file():
        return None
    rows = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.sort(key=lambda row: row.get("ts") or 0)
    return rows


def windows(trace, plan_action, item, n):
    """Step iteration windows of one plan: [(start, end)], at most n.

    Plan accepted = first `complete` (exit 0) whose `accepted` lists (step-plan, item). Window k starts at the first
    `implement` packet for the item printed after the plan was accepted (k = 1) or after window k-1 ended, and ends at
    the first `complete` (exit 0) whose `accepted` lists (document, item) after that start (the next window may start up to
    that call's `ms` + 1 s before its row's ts, since that call prints the next packet). Windows stop at the next
    step-plan packet for the same item (a re-plan). The step is the k-th window (list order = execution order)."""
    accepted_at, stop = None, None
    for row in trace:
        if accepted_at is None and row.get("kind") == "command" and row.get("verb") == "complete" \
                and row.get("exit") == 0 and any(a.get("stage") == "step-plan" and a.get("action") == plan_action
                                                  for a in row.get("accepted") or []):
            accepted_at = row["ts"]
        elif accepted_at is not None and row.get("kind") == "packet" and row.get("stage") == "step-plan" \
                and row.get("item") == item and row.get("action") != plan_action:
            stop = row["ts"]
            break
    if accepted_at is None:
        return [], "plan not accepted in trace"
    starts, ends = [], []
    for row in trace:
        ts = row.get("ts") or 0
        if ts < accepted_at - 5.0 or (stop is not None and ts >= stop):
            continue
        if row.get("kind") == "packet" and row.get("stage") == "implement" and row.get("item") == item:
            starts.append(ts)
        elif row.get("kind") == "command" and row.get("verb") == "complete" and row.get("exit") == 0 \
                and any(a.get("stage") == "document" and a.get("item") == item for a in row.get("accepted") or []):
            ends.append((ts, ts - (row.get("ms") or 0) / 1000 - 1.0))
    out, cursor, used = [], accepted_at - 5.0, -1
    while len(out) < n:
        start = next((ts for ts in starts if ts >= cursor), None)
        k = next((k for k, (ts, _) in enumerate(ends) if k > used and ts > (start or 0)), None) \
            if start is not None else None
        if k is None:
            break
        out.append((start, ends[k][0]))
        cursor, used = ends[k][1], k
    return out, None


def commit_check(run: pathlib.Path, plan_action, item, trace, wins):
    """Cross-check: iterations/<item>.json maps step -> commit; commits/<implement action>.txt maps an implement
    action -> commit. Returns (checked, agree): does each window contain its step's implement packet?"""
    try:
        plan = json.loads((run / "iterations" / f"{item}.json").read_text())["plans"][plan_action]
    except (OSError, KeyError, ValueError, TypeError):
        return 0, 0
    by_commit = {}
    for path in sorted((run / "commits").glob("*.txt")):
        by_commit.setdefault(path.read_text().strip(), path.stem)
    first_packet = {}
    for row in trace:
        if row.get("kind") == "packet":
            first_packet.setdefault(row.get("action"), row.get("ts"))
    checked = agree = 0
    for step, record in sorted(plan.items(), key=lambda kv: kv[1].get("number", 0)):
        k = record.get("number", 0) - 1
        action = by_commit.get(str(record.get("commit")))
        if action is None or action not in first_packet or not 0 <= k < len(wins):
            continue
        checked += 1
        agree += wins[k][0] <= first_packet[action] <= wins[k][1]
    return checked, agree


def critical_path(durations, steps, ancestors_unused=None):
    ids = [str(step.get("id")) for step in steps]
    position = {sid: i for i, sid in enumerate(ids)}
    finish = []
    for i, step in enumerate(steps):
        deps = [position[str(d)] for d in step.get("deps") or [] if position.get(str(d), len(steps)) < i]
        finish.append(durations[i] + max((finish[d] for d in deps), default=0.0))
    return max(finish)


# ---------------------------------------------------------------- census

def run_date(run: pathlib.Path, trace):
    try:
        started = json.loads((run / "timeline.json").read_text()).get("started")
        if started:
            return started[:10], "timeline.json started"
    except (OSError, ValueError, AttributeError):
        pass
    if trace:
        return datetime.datetime.fromtimestamp(trace[0]["ts"], datetime.timezone.utc).strftime("%Y-%m-%d"), "trace"
    return None, None


def collect(roots):
    copies = collections.defaultdict(list)
    for root in roots:
        for path in sorted(pathlib.Path(root).rglob("results/*.md")):
            try:
                if '"step-plan"' not in path.read_text(encoding="utf-8", errors="replace"):
                    continue
            except OSError:
                continue
            block = state_block(path)
            if not block or block.get("stage") != "step-plan" or not block.get("action"):
                continue
            steps = (block.get("result") or {}).get("steps")
            if not isinstance(steps, list):
                continue
            copies[block["action"]].append((path, block))
    return copies


def census(roots):
    copies = collect(roots)
    rows, states, traces = [], {}, {}
    differing = 0
    for action in sorted(copies):
        versions = {hashlib.sha256(json.dumps(b["result"]["steps"], sort_keys=True).encode()).hexdigest()
                    for _, b in copies[action]}
        differing += len(versions) > 1
        best = None
        for path, block in copies[action]:  # prefer the copy whose trace yields the most step windows
            run = path.parent.parent
            if run not in traces:
                traces[run] = load_trace(run)
            steps = block["result"]["steps"]
            wins, why = (windows(traces[run], action, block.get("workitem"), len(steps)) if traces[run]
                         else ([], "no trace.jsonl"))
            score = (len(wins), traces[run] is not None)
            if best is None or score > best[0]:
                best = (score, path, block, wins, why)
        _, path, block, wins, why = best
        run = path.parent.parent
        if run not in states:
            states[run] = state_block(run / "state.md") or {}
        steps = block["result"]["steps"]
        request = normalise(str(states[run].get("prompt") or ""))
        row = shape(steps)
        anc, indep = row.pop("_ancestors", None), row.pop("_indep", None)
        date, date_source = run_date(run, traces.get(run))
        row.update({"action": action, "workitem": block.get("workitem"), "run": str(run), "result": str(path),
                    "copies": len(copies[action]), "family": hashlib.sha256(request.encode()).hexdigest()[:12],
                    "request_head": request[:100], "date": date, "date_source": date_source,
                    "tasks": [str(s.get("task") or "")[:240] for s in steps],
                    "deps": [s.get("deps") for s in steps], "paths": [s.get("paths") or [] for s in steps]})
        if indep is not None:
            same_level = [(i, j) for i, j in indep if row["level"][i] == row["level"][j]]
            row["write_same_level"] = conflicts(steps, same_level)
            row["write_independent"] = conflicts(steps, indep)
        row["windows"] = len(wins)
        row["timing_gap"] = why if not wins else (None if len(wins) == len(steps) else "fewer windows than steps")
        if wins:
            checked, agree = commit_check(run, action, block.get("workitem"), traces[run], wins)
            row["commit_check"] = {"checked": checked, "agree": agree}
        if steps and len(wins) == len(steps):
            durations = [end - start for start, end in wins]
            row["durations_s"] = [round(d, 1) for d in durations]
            row["T_s"] = round(sum(durations), 1)
            if row["class"] != "unknown":
                row["C_s"] = round(critical_path(durations, steps), 1)
                row["saving"] = round(1 - row["C_s"] / row["T_s"], 4) if row["T_s"] else 0.0
        rows.append(row)
    return rows, differing


def share(num, den):
    return {"num": num, "den": den, "share": round(num / den, 4) if den else None}


def dist(values):
    if not values:
        return None
    values = sorted(values)
    q = statistics.quantiles(values, n=4) if len(values) > 1 else [values[0]] * 3
    return {"count": len(values), "mean": round(statistics.mean(values), 4), "p25": round(q[0], 4),
            "median": round(q[1], 4), "p75": round(q[2], 4), "max": round(values[-1], 4), "min": round(values[0], 4)}


def aggregate(rows, differing):
    known = [r for r in rows if r["class"] not in ("unknown", "empty")]
    timed = [r for r in known if "C_s" in r]
    families = collections.defaultdict(list)
    for r in rows:
        families[r["family"]].append(r)
    agg = {
        "population": {
            "step_plans": len(rows), "work_items": len({(r["run"], r["workitem"]) for r in rows}),
            "runs": len({r["run"] for r in rows}), "families": len(families),
            "copies_total": sum(r["copies"] for r in rows), "actions_with_differing_copies": differing,
            "deps_on": dict(sorted(collections.Counter(r["deps_on"] for r in rows).items())),
            "empty_plans": sum(r["class"] == "empty" for r in rows),
            "dates": [min(r["date"] for r in rows if r["date"]), max(r["date"] for r in rows if r["date"])],
            "undated": sum(not r["date"] for r in rows),
            "plans_with_bad_deps": sum(bool(r.get("bad_deps")) for r in known),
        },
        "shape": {
            "denominator": "plans with deps on every step and at least one step",
            "plans": len(known),
            "class": dict(sorted(collections.Counter(r["class"] for r in rows).items())),
            "n": dict(sorted(collections.Counter(r["n"] for r in known).items())),
            "L": dict(sorted(collections.Counter(r["L"] for r in known).items())),
            "W": dict(sorted(collections.Counter(r["W"] for r in known).items())),
            "independent_pair_plans": share(sum(r["L"] < r["n"] for r in known), len(known)),
            "independent_pair_plans_n_ge_2": share(sum(r["L"] < r["n"] for r in known if r["n"] >= 2),
                                                   sum(r["n"] >= 2 for r in known)),
            "pairs": {"total": sum(r["pairs"] for r in known),
                      "independent": sum(r["independent_pairs"] for r in known)},
            "S_levels_assumption_equal_durations": dist([r["S_levels"] for r in known]),
            "S_levels_pooled_sum_n_over_sum_L": round(sum(r["n"] for r in known) / sum(r["L"] for r in known), 4),
        },
        "write_sets": {},
        "durations": {
            "denominator": "plans with deps on every step and one window per step",
            "timed_plans": len(timed), "timed_runs": len({r["run"] for r in timed}),
            "timing_gaps": dict(sorted(collections.Counter(r["timing_gap"] or "complete" for r in known).items())),
            "commit_check": {"checked": sum(r.get("commit_check", {}).get("checked", 0) for r in rows),
                             "agree": sum(r.get("commit_check", {}).get("agree", 0) for r in rows)},
        },
    }
    for key in ("write_same_level", "write_independent"):
        tot = collections.Counter()
        for r in known:
            tot.update(r[key])
        agg["write_sets"][key] = {**dict(tot), "overlap_share_of_pairs_with_paths":
                                  round(tot["overlap"] / (tot["overlap"] + tot["disjoint"]), 4)
                                  if tot["overlap"] + tot["disjoint"] else None,
                                  "plans_with_any_pair": sum(r[key]["pairs"] > 0 for r in known),
                                  "plans_with_a_disjoint_pair": sum(r[key]["disjoint"] > 0 for r in known)}
    if timed:
        T, C = sum(r["T_s"] for r in timed), sum(r["C_s"] for r in timed)
        multi = [r for r in timed if r["n"] >= 2]
        agg["durations"].update({
            "sum_T_s": round(T, 1), "sum_C_s": round(C, 1), "time_weighted_saving": round(1 - C / T, 4),
            "saving_per_plan": dist([r["saving"] for r in timed]),
            "saving_per_plan_n_ge_2": dist([r["saving"] for r in multi]),
            "n_ge_2": {"plans": len(multi), "sum_T_s": round(sum(r["T_s"] for r in multi), 1),
                       "sum_C_s": round(sum(r["C_s"] for r in multi), 1),
                       "time_weighted_saving": round(1 - sum(r["C_s"] for r in multi) / sum(r["T_s"] for r in multi), 4)
                       if multi else None},
            "plans_with_saving_gt_0": share(sum(r["saving"] > 0 for r in timed), len(timed)),
            "step_seconds": dist([d for r in timed for d in r["durations_s"]]),
            "S_levels_on_timed_plans": round(sum(r["n"] for r in timed) / sum(r["L"] for r in timed), 4),
        })
    # family-weighted: each family counts once (mean of its plans' indicator / value)
    fam_known = {f: [r for r in rs if r in known] for f, rs in families.items()}
    fam_known = {f: rs for f, rs in fam_known.items() if rs}
    fam_timed = {f: [r for r in rs if "C_s" in r] for f, rs in fam_known.items()}
    fam_timed = {f: rs for f, rs in fam_timed.items() if rs}
    agg["per_family"] = {
        "families_total": len(families), "families_with_known_shape": len(fam_known),
        "plans_per_family": dist([len(rs) for rs in families.values()]),
        "family_weighted_independent_pair_share": round(statistics.mean(
            statistics.mean(r["L"] < r["n"] for r in rs) for rs in fam_known.values()), 4) if fam_known else None,
        "families_with_any_independent_pair_plan": sum(any(r["L"] < r["n"] for r in rs) for rs in fam_known.values()),
        "family_weighted_S_levels": round(statistics.mean(
            statistics.mean(r["S_levels"] for r in rs) for rs in fam_known.values()), 4) if fam_known else None,
        "families_timed": len(fam_timed),
        "family_weighted_saving": round(statistics.mean(
            statistics.mean(r["saving"] for r in rs) for rs in fam_timed.values()), 4) if fam_timed else None,
        "family_time_weighted_saving": round(statistics.mean(
            1 - sum(r["C_s"] for r in rs) / sum(r["T_s"] for r in rs) for rs in fam_timed.values()
            if sum(r["T_s"] for r in rs)), 4) if fam_timed else None,
        "families": {f: {"plans": len(rs), "request_head": rs[0]["request_head"],
                         "classes": dict(sorted(collections.Counter(r["class"] for r in rs).items()))}
                     for f, rs in sorted(families.items())},
    }
    return agg


def main(argv):
    roots = [pathlib.Path(a) for a in argv] or sorted(pathlib.Path("/Users/dadleet").glob("e2e-runs*"))
    rows, differing = census(roots)
    agg = aggregate(rows, differing)
    EVIDENCE.mkdir(exist_ok=True)
    out = {"roots": [str(r) for r in roots], "aggregate": agg, "plans": rows}
    (EVIDENCE / "census.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    p, s, w, d, f = agg["population"], agg["shape"], agg["write_sets"], agg["durations"], agg["per_family"]
    print(f"population: {p['step_plans']} step plans ({p['copies_total']} copies), {p['work_items']} work items, "
          f"{p['runs']} runs, {p['families']} families, dates {p['dates'][0]}..{p['dates'][1]}; deps on {p['deps_on']}")
    print(f"classes: {s['class']}")
    print(f"shape ({s['plans']} plans with deps): independent-pair plans {s['independent_pair_plans']}, "
          f"n>=2 {s['independent_pair_plans_n_ge_2']}; pairs {s['pairs']}; L {s['L']}; W {s['W']}")
    print(f"S=n/L (assumes equal step durations): per-plan {s['S_levels_assumption_equal_durations']}, "
          f"pooled {s['S_levels_pooled_sum_n_over_sum_L']}")
    print(f"write sets, same-level pairs: {w['write_same_level']}")
    print(f"write sets, all independent pairs: {w['write_independent']}")
    print(f"durations: {d}")
    print(f"per family: { {k: v for k, v in f.items() if k != 'families'} }")


if __name__ == "__main__":
    main(sys.argv[1:])
