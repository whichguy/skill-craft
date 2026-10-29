"""Tables for docs/shiploop-improve-value-journal.md from the extracted rows.

Usage:  python3 -I analyze.py [EVIDENCE_DIR]

Reads runs.json, reviews.json, passes.json and review-text.json (from extract.py)
and labels/out-*.json (the finding-level labels, see classification-prompt.md).
Writes findings.json (labelled findings joined to their pass), tables.md and
summary.json into EVIDENCE_DIR.
"""
import collections
import glob
import json
import os
import statistics
import sys

EVIDENCE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
NAMED = {
    "battleship": "e2e-runs/20261028/pa-ds-battleship-4ed4e3",
    "hello": "e2e-runs-owner-note/20261028/pc-ds-hello-note-b45e87",
}
GROUPS = {
    "spec": "planning", "test-strategy": "planning", "plan": "planning", "release-plan": "planning",
    "step-plan": "step-level planning", "test-spec": "step-level planning",
    "implement": "build", "system-test-author": "build",
    "carry-forward": "carry-forward",
}
GROUP_ORDER = ["planning", "step-level planning", "build", "carry-forward"]
STAGE_ORDER = ["spec", "test-strategy", "plan", "release-plan", "step-plan", "test-spec", "implement",
               "system-test-author", "carry-forward"]
PRODUCT_KINDS = {"code", "test"}


def load(name):
    with open(os.path.join(EVIDENCE, name), encoding="utf-8") as handle:
        return json.load(handle)


def pct(part, whole):
    return "%d%%" % round(100 * part / whole) if whole else "-"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def kinds(pass_row):
    found = set(pass_row["buckets"])
    if pass_row["result_changed"]:
        found.add("run-result")
    return found


def effect(pass_row):
    """product (code or tests), records (everything else edited) or none."""
    if pass_row["outcome"] == "none":
        return "none"
    return "product" if pass_row["outcome"] == "product" else "records"  # "unrecorded" counts with records


def size_class(run):
    items, steps = run.get("items_planned"), run.get("steps_first_plan")
    if items is None:
        return "no plan reached"
    if items >= 2:
        return "2+ items"
    return "1 item, 1 step" if steps == 1 else "1 item, 2+ steps"


def mins(seconds):
    return "%.1f" % (seconds / 60.0)


def labelled_findings(passes_by_id):
    """Flatten labels/out-*.json, check them against the git facts of each pass."""
    labelled, problems = [], collections.Counter()
    seen = set()
    for path in sorted(glob.glob(os.path.join(EVIDENCE, "labels", "out-*.json"))):
        with open(path, encoding="utf-8") as handle:
            for item in json.load(handle):
                pass_row = passes_by_id.get(item["id"])
                if pass_row is None:
                    problems["unknown pass id"] += 1
                    continue
                if item["id"] in seen:
                    problems["duplicate pass id"] += 1
                    continue
                seen.add(item["id"])
                allowed = kinds(pass_row) | {"nothing"}
                for index, finding in enumerate(item["findings"], 1):
                    touched = [t for t in finding["touched"]]
                    if not set(touched) <= allowed:
                        problems["touched kind not among the pass's real changes"] += 1
                    labelled.append({
                        "id": item["id"], "index": index, "stage": pass_row["stage"],
                        "summary": finding["summary"], "touched": touched, "nature": finding["nature"],
                        "attribution": finding.get("attribution"),
                        "consistent": set(touched) <= allowed,
                    })
    return labelled, seen, problems


def finding_effect(finding):
    touched = set(finding["touched"])
    if touched & PRODUCT_KINDS:
        return "product"
    if touched - {"nothing"}:
        return "records"
    return "unacted"


def main():
    runs, reviews = load("runs.json"), load("reviews.json")
    passes, texts = load("passes.json"), load("review-text.json")
    for p in passes:
        p["id"] = "%s|%s|%d" % (p["run"], p["child"], p["pass"])
    passes_by_id = {p["id"]: p for p in passes}
    run_by_id = {r["run"]: r for r in runs}
    for p in passes:
        p["group"] = GROUPS.get(p["stage"], "other")
        p["size"] = size_class(run_by_id[p["run"]])
    findings, labelled_ids, problems = labelled_findings(passes_by_id)
    expected = {t["id"] for t in texts}
    problems["passes without labels"] = len(expected - labelled_ids)
    for f in findings:
        f["effect"] = finding_effect(f)
        p = passes_by_id[f["id"]]
        f.update(run=p["run"], child=p["child"], pass_number=p["pass"], group=p["group"], size=p["size"])
    # a product pass "changed behaviour" when a labelled finding fixed in code or tests is a behaviour defect;
    # the other product passes edited comments, docstrings or wrapping only
    behaviour = {f["id"] for f in findings if f["effect"] == "product" and f["nature"] == "behaviour-defect"}
    for p in passes:
        p["behaviour"] = p["id"] in behaviour
    with open(os.path.join(EVIDENCE, "findings.json"), "w", encoding="utf-8") as handle:
        json.dump(findings, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")

    out, summary = [], {}

    # ---- per named run: one row per Improve child
    for label, run_id in NAMED.items():
        rows = []
        for child in [r for r in reviews if r["run"] == run_id]:
            cp = sorted((p for p in passes if p["run"] == run_id and p["child"] == child["child"]), key=lambda p: p["pass"])
            seq = "; ".join("%d %s %s" % (p["pass"], "N" if p["label"] == "non-trivial" else "T",
                            "product-behaviour" if p["behaviour"] else ("product-comments" if effect(p) == "product" else effect(p))) for p in cp)
            files = collections.Counter(f for p in cp for f in p["files"])
            fl = [f for f in findings if f["run"] == run_id and f["child"] == child["child"]]
            by_effect = collections.Counter(f["effect"] for f in fl)
            changed = ", ".join("`%s`%s" % (f, " x%d" % n if n > 1 else "") for f, n in files.most_common(4))
            if any(p["result_changed"] for p in cp):
                changed += (", " if changed else "") + "stage result"
            if len(files) > 4:
                changed += ", +%d more files" % (len(files) - 4)
            rows.append([
                child["stage"], child["workitem"] or "-", len(cp), seq, len(fl),
                "%d / %d / %d" % (by_effect["product"], by_effect["records"], by_effect["unacted"]),
                mins(sum(p["seconds"] or 0 for p in cp)), changed or "-",
            ])
        rows.sort(key=lambda r: (STAGE_ORDER.index(r[0]) if r[0] in STAGE_ORDER else 99, r[1]))
        run = run_by_id[run_id]
        out.append("### %s: %s\n" % (label, run_id))
        out.append("Model `%s`, ShipLoop %s, plan: %s planned items (%s added later), %s steps; active %s min, Improve %s min.\n" % (
            run["model"], run["shiploop_version"], run["items_planned"], run["items_added_after_plan"],
            run["steps_first_plan"], mins(run["active_seconds"] or 0), mins(run["improve_seconds"])))
        out.append(table(
            ["stage", "item", "passes", "passes (N non-trivial / T trivial; what the pass edited)", "findings",
             "product / records / unacted", "min", "files changed"], rows))
        out.append("")

    # ---- all runs by stage
    rows = []
    for stage in STAGE_ORDER:
        sp = [p for p in passes if p["stage"] == stage]
        if not sp:
            continue
        children = len({(p["run"], p["child"]) for p in sp})
        e = collections.Counter(effect(p) for p in sp)
        fl = [f for f in findings if f["stage"] == stage]
        fe = collections.Counter(f["effect"] for f in fl)
        sec = sum(p["seconds"] or 0 for p in sp)
        rows.append([stage, GROUPS[stage], children, len(sp), sum(1 for p in sp if p["label"] == "non-trivial"),
                     e["product"], sum(1 for p in sp if p["behaviour"]), e["records"], e["none"], len(fl), fe["product"], fe["records"], fe["unacted"], mins(sec)])
    out.append("### All %d runs, by stage\n" % len(runs))
    out.append(table(["stage", "group", "children", "passes", "non-trivial", "passes editing product", "of which behaviour", "passes editing records only",
                      "passes editing nothing", "findings", "product", "records", "unacted", "min"], rows))
    out.append("")

    # ---- by plan size and stage group
    rows = []
    for size in ["1 item, 1 step", "1 item, 2+ steps", "2+ items"]:
        n_runs = sum(1 for r in runs if size_class(r) == size)
        for group in GROUP_ORDER:
            sp = [p for p in passes if p["size"] == size and p["group"] == group]
            if not sp:
                continue
            e = collections.Counter(effect(p) for p in sp)
            fl = [f for f in findings if f["size"] == size and f["group"] == group]
            fe = collections.Counter(f["effect"] for f in fl)
            sec = sum(p["seconds"] or 0 for p in sp)
            rows.append([size, n_runs, group, len({(p["run"], p["child"]) for p in sp}), len(sp),
                         sum(1 for p in sp if p["label"] == "non-trivial"), e["product"], sum(1 for p in sp if p["behaviour"]), e["records"], e["none"],
                         len(fl), fe["product"], fe["records"], fe["unacted"], mins(sec), mins(sec / n_runs)])
    out.append("### By plan size and stage group\n")
    out.append("Plan size is the planned work items and the steps of the first accepted step plans.\n")
    out.append(table(["plan size", "runs", "group", "children", "passes", "non-trivial", "product", "behaviour", "records only", "nothing",
                      "findings", "f: product", "f: records", "f: unacted", "min total", "min per run"], rows))
    out.append("")

    # ---- minutes versus product edits, by stage group (all runs, then ShipLoop 1.16 and later)
    def at_least(run, version):
        return tuple(int(x) for x in run["shiploop_version"].split(".")[:2]) >= version

    rows = []
    for label, keep in (("all 25 runs", lambda r: True), ("ShipLoop 1.16 and later (5 runs)", lambda r: at_least(r, (1, 16)))):
        runs_in = {r["run"] for r in runs if keep(r)}
        total = sum(p["seconds"] or 0 for p in passes if p["run"] in runs_in)
        for names, groups in (("planning", ("planning",)), ("step-level planning", ("step-level planning",)),
                              ("build + carry-forward", ("build", "carry-forward"))):
            sp = [p for p in passes if p["run"] in runs_in and p["group"] in groups]
            sec = sum(p["seconds"] or 0 for p in sp)
            fl = [f for f in findings if f["run"] in runs_in and f["group"] in groups]
            fe = collections.Counter(f["effect"] for f in fl)
            nb = sum(1 for p in sp if p["behaviour"])
            rows.append([label, names, len(sp), mins(sec), pct(sec, total), sum(1 for p in sp if p["outcome"] == "product"), nb,
                         len(fl), fe["product"], fe["records"], mins(sec / nb) if nb else "-"])
    out.append("### Improve minutes and product edits, by stage group\n")
    out.append(table(["runs", "stage group", "passes", "min", "share of Improve min", "passes editing product", "behaviour passes",
                      "findings", "f: product", "f: records", "min per behaviour pass"], rows))
    out.append("")

    # ---- how the work scales with plan size (per run)
    rows = []
    for size in ["1 item, 1 step", "1 item, 2+ steps", "2+ items"]:
        rs = [r for r in runs if size_class(r) == size]
        n = len(rs)
        ids = {r["run"] for r in rs}
        sp = [p for p in passes if p["run"] in ids]
        plan_p = [p for p in sp if p["group"] == "planning"]
        build_p = [p for p in sp if p["group"] in ("build", "carry-forward")]
        plan_f = [f for f in findings if f["run"] in ids and f["group"] == "planning" and f["effect"] != "unacted"]
        active = sum(r["active_seconds"] or r["wall_seconds"] or 0 for r in rs)
        imp = sum(p["seconds"] or 0 for p in sp)
        rows.append([size, n, mins(active / n), mins(imp / n), pct(imp, active), mins(sum(p["seconds"] or 0 for p in plan_p) / n),
                     "%.1f" % (len(plan_f) / n), "%.1f" % (sum(1 for p in build_p if p["behaviour"]) / n),
                     "%d / %d" % (sum(1 for p in build_p if p["behaviour"]), len(build_p))])
    out.append("### How Improve scales with plan size, per run\n")
    out.append(table(["plan size", "runs", "active min", "Improve min", "Improve share", "planning min", "planning fixes",
                      "build behaviour passes", "behaviour passes / build passes"], rows))
    out.append("")

    # ---- size class x stage
    rows = []
    for size in ["1 item, 1 step", "1 item, 2+ steps", "2+ items"]:
        for stage in STAGE_ORDER:
            sp = [p for p in passes if p["size"] == size and p["stage"] == stage]
            if not sp:
                continue
            children = {(p["run"], p["child"]) for p in sp}
            e = collections.Counter(effect(p) for p in sp)
            fl = [f for f in findings if f["size"] == size and f["stage"] == stage]
            fe = collections.Counter(f["effect"] for f in fl)
            first = sum(1 for c in children if any(p["pass"] == 1 and effect(p) != "none" for p in sp if (p["run"], p["child"]) == c))
            rows.append([size, stage, len(children), len(sp), e["product"], sum(1 for p in sp if p["behaviour"]), e["records"], e["none"], first,
                         len(fl), fe["product"], fe["records"], mins(sum(p["seconds"] or 0 for p in sp))])
    out.append("### By plan size and stage\n")
    out.append(table(["plan size", "stage", "children", "passes", "product", "behaviour", "records only", "nothing",
                      "children edited in pass 1", "findings", "f: product", "f: records", "min"], rows))
    out.append("")

    # ---- spread of planning cost on one-item plans
    one_set = {"1 item, 1 step", "1 item, 2+ steps"}
    rows = []
    for r in sorted((r for r in runs if size_class(r) in one_set), key=lambda r: r["run"]):
        rp = [p for p in passes if p["run"] == r["run"] and p["group"] == "planning"]
        active = r["active_seconds"] or r["wall_seconds"] or 0
        rows.append([r["run"].split("/", 1)[1][:44], r["model"][:20] if r["model"] else "-", r["shiploop_version"],
                     size_class(r), len(rp), mins(sum(p["seconds"] or 0 for p in rp)),
                     pct(sum(p["seconds"] or 0 for p in rp), active), mins(r["improve_seconds"]), mins(active)])
    out.append("### Planning-stage Improve cost, one-item runs\n")
    out.append(table(["run", "model", "ShipLoop", "plan size", "planning passes", "planning min", "share of active",
                      "all Improve min", "active min"], rows))
    out.append("")
    shares = [sum(p["seconds"] or 0 for p in passes if p["run"] == r["run"] and p["group"] == "planning") /
              (r["active_seconds"] or r["wall_seconds"]) for r in runs if size_class(r) in one_set]
    plan_secs = [sum(p["seconds"] or 0 for p in passes if p["run"] == r["run"] and p["group"] == "planning")
                 for r in runs if size_class(r) in one_set]
    summary["one_item_planning_share_median"] = round(statistics.median(shares), 3)
    summary["one_item_planning_share_min"] = round(min(shares), 3)
    summary["one_item_planning_share_max"] = round(max(shares), 3)
    summary["one_item_planning_seconds_median"] = round(statistics.median(plan_secs))
    summary["one_item_planning_seconds_min"] = min(plan_secs)
    summary["one_item_planning_seconds_max"] = max(plan_secs)

    # ---- where the acted findings land by pass number (planning stages, one-item plans)
    rows = []
    for number in (1, 2, 3, 4):
        sp = [p for p in passes if p["group"] == "planning" and p["size"] in one_set and (p["pass"] == number if number < 4 else p["pass"] >= 4)]
        fl = [f for f in findings if f["group"] == "planning" and f["size"] in one_set and (f["pass_number"] == number if number < 4 else f["pass_number"] >= 4) and f["effect"] != "unacted"]
        rows.append([("%d" % number) if number < 4 else "4+", len(sp), sum(1 for p in sp if effect(p) != "none"), len(fl),
                     mins(sum(p["seconds"] or 0 for p in sp))])
    out.append("### Planning stages, one-item plans, by pass number\n")
    out.append(table(["pass", "passes", "passes that edited", "findings acted on", "min"], rows))
    out.append("")

    # ---- do later stages still fix records on one-item plans? (cross-coverage)
    rows = []
    for group in ("planning", "step-level planning", "build", "carry-forward"):
        fl = [f for f in findings if f["group"] == group and f["size"] in one_set and f["effect"] == "records"]
        nat = collections.Counter(f["nature"] for f in fl)
        rows.append([group, len(fl), nat["contradiction-or-unverifiable"], nat["stale-or-wrong-reference"],
                     nat["missing-content"], nat["behaviour-defect"], nat["polish"]])
    out.append("### Findings fixed in records only, one-item plans, by the stage that found them\n")
    out.append(table(["stage group", "record-only findings", "contradiction / unverifiable", "stale / wrong reference",
                      "missing content", "behaviour defect", "polish"], rows))
    out.append("")

    # ---- planning stages on one-item plans, per stage
    one = {"1 item, 1 step", "1 item, 2+ steps"}
    rows = []
    for stage in ["spec", "test-strategy", "plan", "release-plan"]:
        sp = [p for p in passes if p["stage"] == stage and p["size"] in one]
        e = collections.Counter(effect(p) for p in sp)
        fl = [f for f in findings if f["stage"] == stage and f["size"] in one]
        nat = collections.Counter(f["nature"] for f in fl if f["effect"] != "unacted")
        sec = sum(p["seconds"] or 0 for p in sp)
        children = {(p["run"], p["child"]) for p in sp}
        first_edit = sum(1 for c in children if any(p["pass"] == 1 and effect(p) != "none" for p in sp if (p["run"], p["child"]) == c))
        idle = sum(p["seconds"] or 0 for p in sp if p["outcome"] == "none")
        rows.append([stage, len(children), len(sp), e["product"], e["records"], e["none"], first_edit,
                     len(fl), nat["contradiction-or-unverifiable"], nat["behaviour-defect"], nat["stale-or-wrong-reference"],
                     nat["missing-content"], nat["polish"], mins(sec), mins(idle)])
    out.append("### Planning stages on one-item plans\n")
    out.append(table(["stage", "children", "passes", "product", "records only", "nothing", "children edited in pass 1", "findings acted on",
                      "contradiction / unverifiable", "behaviour defect", "stale / wrong reference", "missing content", "polish", "min", "min in passes that edited nothing"], rows))
    out.append("")

    # ---- nature by stage group (acted findings)
    rows = []
    for group in GROUP_ORDER:
        fl = [f for f in findings if f["group"] == group and f["effect"] != "unacted"]
        nat = collections.Counter(f["nature"] for f in fl)
        rows.append([group, len(fl)] + [nat[n] for n in ("behaviour-defect", "contradiction-or-unverifiable",
                     "stale-or-wrong-reference", "missing-content", "polish")])
    out.append("### Nature of acted-on findings, by stage group (all runs)\n")
    out.append(table(["group", "findings", "behaviour defect", "contradiction / unverifiable", "stale / wrong reference",
                      "missing content", "polish"], rows))
    out.append("")

    # ---- per run
    rows = []
    for r in sorted(runs, key=lambda r: r["run"]):
        rp = [p for p in passes if p["run"] == r["run"]]
        plan_p = [p for p in rp if p["group"] == "planning"]
        rows.append([r["run"].split("/", 1)[1][:48], r["case"], r["model"][:22] if r["model"] else "-", r["shiploop_version"],
                     r["items_planned"], r["steps_first_plan"], r["improve_children"], len(rp),
                     sum(1 for p in rp if p["outcome"] == "product"),
                     sum(1 for p in plan_p if p["outcome"] == "product"),
                     mins(sum(p["seconds"] or 0 for p in plan_p)), mins(r["improve_seconds"]),
                     mins(r["active_seconds"] or r["wall_seconds"] or 0), pct(r["improve_seconds"], r["active_seconds"] or r["wall_seconds"]),
                     r["stage_final"]])
    out.append("### Per run\n")
    out.append(table(["run", "case", "model", "ShipLoop", "items", "steps", "children", "passes", "product passes",
                      "planning product passes", "planning min", "Improve min", "active min", "Improve share", "final stage"], rows))
    out.append("")

    # ---- summary numbers
    one_runs = [r for r in runs if size_class(r) in one]
    done_one = [r for r in one_runs if r["stage_final"] == "done"]
    plan_one = [p for p in passes if p["group"] == "planning" and p["size"] in one]
    summary.update({
        "runs": len(runs), "children": len(reviews), "passes": len(passes), "findings_labelled": len(findings),
        "labels_problems": dict(problems),
        "one_item_runs": len(one_runs), "one_item_runs_done": len(done_one),
        "product_passes": sum(1 for p in passes if p["outcome"] == "product"),
        "behaviour_passes": sum(1 for p in passes if p["behaviour"]),
        "findings_by_effect": dict(collections.Counter(f["effect"] for f in findings)),
        "planning_passes_one_item": len(plan_one),
        "planning_passes_one_item_product": sum(1 for p in plan_one if p["outcome"] == "product"),
        "planning_seconds_one_item": sum(p["seconds"] or 0 for p in plan_one),
        "improve_seconds_one_item_done_runs": sum(r["improve_seconds"] for r in done_one),
        "active_seconds_one_item_done_runs": sum(r["active_seconds"] or r["wall_seconds"] or 0 for r in done_one),
        "planning_seconds_one_item_done_runs": sum(p["seconds"] or 0 for p in plan_one if run_by_id[p["run"]]["stage_final"] == "done"),
    })
    # ---- further numbers quoted by the journal
    done_runs = [r for r in runs if r["stage_final"] == "done"]
    shares_all = [r["improve_seconds"] / (r["active_seconds"] or r["wall_seconds"]) for r in done_runs]
    summary["improve_share_done_runs"] = {
        "n": len(done_runs), "median": round(statistics.median(shares_all), 3),
        "min": round(min(shares_all), 3), "max": round(max(shares_all), 3)}
    summary["improve_minutes_all"] = round(sum(p["seconds"] or 0 for p in passes) / 60, 1)
    summary["planning_minutes_all"] = round(sum(p["seconds"] or 0 for p in passes if p["group"] == "planning") / 60, 1)
    summary["passes_non_trivial"] = sum(1 for p in passes if p["label"] == "non-trivial")
    summary["passes_edited_anything"] = sum(1 for p in passes if p["outcome"] != "none")
    summary["passes_unrecorded_edit"] = sum(1 for p in passes if p["outcome"] == "unrecorded")
    build_like = [p for p in passes if p["group"] in ("build", "carry-forward")]
    summary["build_carry_passes"] = len(build_like)
    summary["build_carry_product_passes"] = sum(1 for p in build_like if p["outcome"] == "product")
    summary["build_carry_behaviour_passes"] = sum(1 for p in build_like if p["behaviour"])
    for size in ("1 item, 1 step", "1 item, 2+ steps", "2+ items"):
        sub = [p for p in build_like if p["size"] == size]
        summary["build_carry_behaviour_" + size] = "%d/%d" % (sum(1 for p in sub if p["behaviour"]), len(sub))
    for label, run_id in NAMED.items():
        rp = [p for p in passes if p["run"] == run_id]
        rf = [f for f in findings if f["run"] == run_id]
        summary["named_" + label] = {
            "children": len({p["child"] for p in rp}), "passes": len(rp),
            "findings": len(rf), "findings_by_effect": dict(collections.Counter(f["effect"] for f in rf)),
            "product_passes": sum(1 for p in rp if p["outcome"] == "product"),
            "behaviour_passes": sum(1 for p in rp if p["behaviour"]),
            "improve_min": round(sum(p["seconds"] or 0 for p in rp) / 60, 1),
            "planning_min": round(sum(p["seconds"] or 0 for p in rp if p["group"] == "planning") / 60, 1),
            "active_min": round((run_by_id[run_id]["active_seconds"] or 0) / 60, 1)}
    fam = collections.defaultdict(list)
    for r in runs:
        if size_class(r) in one_set:
            family = "claude" if "claude" in (r["model"] or "") else ("deepseek" if "deepseek" in (r["model"] or "") else (r["model"] or "other"))
            fam[family].append(sum(p["seconds"] or 0 for p in passes if p["run"] == r["run"] and p["group"] == "planning"))
    summary["one_item_planning_seconds_by_model_family"] = {
        k: {"runs": len(v), "median": round(statistics.median(v)), "min": min(v), "max": max(v)} for k, v in sorted(fam.items())}
    out.append("### Label checks\n")
    out.append("`%s`\n" % json.dumps(dict(problems)))
    with open(os.path.join(EVIDENCE, "tables.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out).rstrip("\n") + "\n")
    with open(os.path.join(EVIDENCE, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
