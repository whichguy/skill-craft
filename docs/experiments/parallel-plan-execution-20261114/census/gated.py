#!/usr/bin/env python3
"""gated.py: the census's ideal saving once steps that share files must stay in list order (a conflict-aware bound).

Reads evidence/census.json (the per-plan rows census.py wrote: deps, paths and per-step iteration seconds) and writes
evidence/gated.txt. It adds one question the census left open: if two steps with no dependency path may not run at the
same time when their declared `paths` overlap, how much of the ideal saving is left? The bound is still ideal: unlimited
workers, unchanged step times, no merge cost; steps that conflict run in the plan's list order.

  python3 -I gated.py            prints the summary and writes evidence/gated.txt

Overlap rule (census README): paths equal, or one a directory prefix of the other, after stripping ./ and a trailing /;
a glob is cut to its fixed directory prefix, and a top-level glob overlaps everything. Two readings of a step with no
`paths` are reported: STRICT (it conflicts with every other step) and FREE (it conflicts with none).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def prefix(path: str) -> str:
    path = path.strip()
    while path.startswith("./"):
        path = path[2:]
    fixed = []
    for part in path.rstrip("/").split("/"):
        if any(c in part for c in "*?["):
            break
        fixed.append(part)
    return "/".join(fixed)


def overlap(a: list, b: list) -> bool:
    for x in map(prefix, a):
        for y in map(prefix, b):
            if x == "" or y == "" or x == y or x.startswith(y + "/") or y.startswith(x + "/"):
                return True
    return False


def mappable(row: dict) -> bool:
    """True when every dependency name is S<number> naming an earlier position (step ids S1..Sn in list order); the evidence
    rows hold deps by name only, so a plan whose ids do not follow position is skipped and counted, never mis-mapped."""
    for i, dep in enumerate(row.get("deps") or []):
        for name in dep:
            if not (isinstance(name, str) and name[:1] == "S" and name[1:].isdigit() and int(name[1:]) - 1 < i):
                return False
    return True


def finish_times(durations: list, deps: list, extra: dict) -> list:
    """Longest-path finish of each step with unlimited workers; ``extra[i]`` adds predecessors (conflicts)."""
    finish: list = []
    for i, d in enumerate(durations):
        before = [int(name[1:]) - 1 for name in deps[i]] + sorted(extra.get(i, ()))
        finish.append(max([finish[j] for j in before], default=0.0) + d)
    return finish


def analyse(row: dict, unknown_conflicts: bool) -> dict | None:
    durations, deps, paths = row.get("durations_s"), row.get("deps"), row.get("paths")
    n = row["n"]
    if not durations or len(durations) != n or not isinstance(deps, list) or len(deps) != n or not mappable(row):
        return None
    try:
        parents = [{int(name[1:]) - 1 for name in dep} for dep in deps]
    except (ValueError, IndexError, TypeError):
        return None
    anc: list = []
    for i in range(n):
        a: set = set()
        for j in parents[i]:
            a |= {j} | anc[j]
        anc.append(a)
    extra: dict = {}
    disjoint_pairs = conflicting_pairs = 0
    for i in range(n):
        for j in range(i):
            if j in anc[i] or i in anc[j]:
                continue
            unknown = not (paths[i] and paths[j])
            clash = unknown_conflicts if unknown else overlap(paths[i], paths[j])
            if clash:
                extra.setdefault(i, set()).add(j)
                conflicting_pairs += 1
            else:
                disjoint_pairs += 1
    total = sum(durations)
    free = max(finish_times(durations, deps, {}))
    gated = max(finish_times(durations, deps, extra))
    return {"T": total, "C_ideal": free, "C_gated": gated, "n": n, "disjoint_pairs": disjoint_pairs,
            "conflicting_pairs": conflicting_pairs}


def summarise(rows: list, unknown_conflicts: bool) -> dict:
    out = [(r, analyse(r, unknown_conflicts)) for r in rows if r.get("class") != "unknown"]
    timed = [(r, a) for r, a in out if a]
    multi = [(r, a) for r, a in timed if a["n"] >= 2]
    qualifying = [(r, a) for r, a in timed if a["disjoint_pairs"] > 0]
    t = sum(a["T"] for _, a in timed)
    ci = sum(a["C_ideal"] for _, a in timed)
    cg = sum(a["C_gated"] for _, a in timed)
    tm = sum(a["T"] for _, a in multi)
    return {
        "timed_plans": len(timed), "timed_multi_step": len(multi), "T_s": round(t, 1),
        "ideal_saving": round(1 - ci / t, 4) if t else None, "gated_saving": round(1 - cg / t, 4) if t else None,
        "ideal_saving_multi": round(1 - sum(a["C_ideal"] for _, a in multi) / tm, 4) if tm else None,
        "gated_saving_multi": round(1 - sum(a["C_gated"] for _, a in multi) / tm, 4) if tm else None,
        "plans_with_a_disjoint_independent_pair_timed": len(qualifying),
        "time_share_of_those_plans": round(sum(a["T"] for _, a in qualifying) / t, 4) if t else None,
        "plans_with_gated_saving_above_zero": sum(1 for _, a in timed if a["C_gated"] < a["T"] - 1e-9),
        "plans_with_ideal_saving_above_zero": sum(1 for _, a in timed if a["C_ideal"] < a["T"] - 1e-9),
    }


def structure_counts(rows: list, unknown_conflicts: bool) -> dict:
    """The same gate on structure alone, for every deps-complete plan (timed or not)."""
    plans = pairs_free = pairs_disjoint = skipped = 0
    for row in rows:
        if row.get("class") == "unknown" or row["n"] < 2:
            continue
        if not mappable(row):
            skipped += 1
            continue
        paths, deps, n = row.get("paths"), row.get("deps"), row["n"]
        anc: list = []
        for i in range(n):
            a: set = set()
            for name in deps[i]:
                j = int(name[1:]) - 1
                a |= {j} | anc[j]
            anc.append(a)
        got = False
        for i in range(n):
            for j in range(i):
                if j in anc[i] or i in anc[j]:
                    continue
                pairs_free += 1
                unknown = not (paths[i] and paths[j])
                if not (unknown_conflicts if unknown else overlap(paths[i], paths[j])):
                    pairs_disjoint += 1
                    got = True
        plans += got
    return {"plans_with_a_disjoint_independent_pair": plans, "independent_pairs": pairs_free, "disjoint_pairs": pairs_disjoint,
            "plans_skipped_ids_not_by_position": skipped}


def main() -> int:
    data = json.loads((HERE / "evidence" / "census.json").read_text())
    rows = data["plans"]
    lines = ["conflict-aware bound over evidence/census.json (ideal: unlimited workers, unchanged step times, no merge cost)",
             f"plans in the evidence: {len(rows)}"]
    for label, strict in (("STRICT (a step with no paths conflicts with every other step)", True),
                          ("FREE (a step with no paths conflicts with none)", False)):
        lines.append("")
        lines.append(label)
        for key, value in summarise(rows, strict).items():
            lines.append(f"  {key}: {value}")
        for key, value in structure_counts(rows, strict).items():
            lines.append(f"  structure, all deps-complete plans with n >= 2, {key}: {value}")
    text = "\n".join(lines) + "\n"
    (HERE / "evidence" / "gated.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
