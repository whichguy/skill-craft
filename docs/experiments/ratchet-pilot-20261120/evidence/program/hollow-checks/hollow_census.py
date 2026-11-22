#!/usr/bin/env python3
"""Mechanical census of nested test runs in acceptance suites.

Site detection is automatic (see cand.py: finds calls whose argument list holds a
`--test` flag or a first-element 'test' argument next to npm/node), and the
per-site facts that need reading code (does the child's env drop
NODE_TEST_CONTEXT; does the test require evidence) are recorded in ann.py,
read by hand from each suite's files.  This script joins both, checks that every
detected site was annotated, and writes census.json / census.txt.

Usage: python3 -I hollow_census.py [--check]
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cand import ROOTS, BASE, suite_files, find_sites, line_of, match_close, TITLE_RE, T1
import ann

OUT = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
DEFECTS = ["default-limit-changed", "resolved-template-replaced", "audit-not-saved"]


def callee_start(text, paren):
    m = re.search(r"([\w$.]+)\s*$", text[max(0, paren - 80):paren])
    return paren - len(m.group(0)) if m else paren


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def title_before(lines, ln):
    for k in range(ln - 1, -1, -1):
        m = TITLE_RE.match(lines[k])
        if m:
            return (m.group(2) or m.group(4) or m.group(6)), k + 1
    return None, None


def item_id(title):
    if not title:
        return None
    m = re.match(r"\s*([A-Z]{1,2}-\d+)\b", title)
    return m.group(1) if m else None


def run_as(rundir, filename):
    """How ratchet/acceptance.json runs the file that holds a call: with node --test or plain node."""
    path = os.path.join(rundir, "work", "ratchet", "acceptance.json")
    if not os.path.exists(path):
        return None
    try:
        data = json.load(open(path))
    except Exception:
        return None
    kinds = set()
    for v in data.values():
        cmd = v.get("command", "") if isinstance(v, dict) else ""
        if filename in cmd:
            kinds.add("node --test" if re.search(r"--test(?![-\w])", cmd) else "plain node")
    return sorted(kinds) or None


def launch_kinds(rundir, texts, runner_files):
    """How ratchet/acceptance.json launches each item: direct `node --test`, a runner script that itself
    spawns `node --test`, or plain `node <file>` (the file registers its own node:test tests)."""
    path = os.path.join(rundir, "work", "ratchet", "acceptance.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    kinds = {}
    for v in d.values():
        c = v.get("command", "") if isinstance(v, dict) else str(v)
        if re.search(r"--test(?![-\w])", c):
            k = "node --test (direct)"
        elif c.strip().startswith("npm test"):
            k = "npm test"
        else:
            m = re.search(r"acceptance/([\w.-]+\.(?:c|m)?js)", c)
            k = "other"
            if m:
                if m.group(1) in runner_files:
                    k = "runner script spawning node --test (" + m.group(1) + ")"
                else:
                    k = "plain node " + m.group(1)
        kinds[k] = kinds.get(k, 0) + 1
    return kinds


def main():
    check = "--check" in sys.argv
    census = []
    problems = []
    scanned = {}
    for root in ROOTS:
        rp = os.path.join(BASE, root)
        n_run = n_acc = 0
        for run in sorted(os.listdir(rp)):
            rd = os.path.join(rp, run)
            if not (os.path.isfile(os.path.join(rd, "run.json")) and os.path.isdir(os.path.join(rd, "work"))):
                continue
            n_run += 1
            ad = os.path.join(rd, "work", "acceptance")
            if not os.path.isdir(ad):
                continue
            n_acc += 1
            rj = json.load(open(os.path.join(rd, "run.json")))
            entry = {
                "root": root, "run": run, "case": rj.get("case"), "host": rj.get("host"),
                "model": rj.get("model"), "effort": rj.get("effort"),
                "enrich": rj.get("enrich"), "preserve": rj.get("preserve"),
                "nested_runs": [], "ignored_runner_calls": [],
            }
            # sites by (file, line, n)
            found = {}
            texts = {}
            for f in suite_files(ad):
                text = open(f, errors="replace").read()
                texts[f] = text
                per_line = {}
                for p, (e, name, kind) in sorted(find_sites(text).items()):
                    ln = line_of(text, p)
                    per_line.setdefault(ln, []).append((p, e, name))
                for ln, lst in per_line.items():
                    for i, (p, e, name) in enumerate(lst):
                        found[(os.path.basename(f), ln, i)] = (f, p, e)
            annotated = ann.ANN.get(run)
            if annotated is None:
                problems.append(f"{run}: no annotations")
                annotated = []
            ignored = {(a, b) for a, b in ann.IGN.get(run, [])}
            used = set()
            for a in annotated:
                key = (a["file"], a["line"], a["n"])
                if a.get("pos"):
                    # manual site: locate by regex from line start
                    fpath = [f for f in texts if os.path.basename(f) == a["file"]][0]
                    text = texts[fpath]
                    start_off = sum(len(l) + 1 for l in text.split("\n")[:a["line"] - 1])
                    m = re.compile(a["pos"]).search(text, start_off)
                    if not m or line_of(text, m.start()) != a["line"]:
                        problems.append(f"{run}: manual site {a['file']}:{a['line']} {a['pos']} not found on that line")
                        continue
                    p = text.index("(", m.start())
                    # callee start for text
                    cs = m.start()
                    e = match_close(text, p)
                    f, p_, e_ = fpath, cs, e
                    call = collapse(text[cs:e + 1])
                    tline = a["line"]
                else:
                    if key not in found:
                        problems.append(f"{run}: annotated site {key} not detected")
                        continue
                    f, p, e = found[key]
                    used.add(key)
                    cs = callee_start(texts[f], p)
                    call = collapse(texts[f][cs:e + 1])
                    tline = a["line"]
                lines = texts[f].split("\n")
                title, tl = title_before(lines, tline)
                for (title_use, ev, quote) in a["uses"]:
                    entry["nested_runs"].append({
                        "file": a["file"], "line": a["line"],
                        "enclosing_test_title_nearest_preceding": title,
                        "enclosing_test_id_nearest_preceding": item_id(title),
                        "test": title_use,
                        "call": call[:200],
                        "env_drops_NODE_TEST_CONTEXT": a["drop"],
                        "env_note": a["dnote"],
                        "requires_evidence": ev,
                        "evidence_quote": quote,
                        "file_run_as": run_as(rd, a["file"]),
                    })
            for key, (f, p, e) in found.items():
                if key in used:
                    continue
                if (key[0], key[1]) in ignored or (key[0], 0) in ignored:
                    # a detected site explicitly recorded as not a nested run (or a runner script call)
                    cs = callee_start(texts[f], p)
                    entry["ignored_runner_calls"].append({
                        "file": key[0], "line": key[1], "call": collapse(texts[f][cs:e + 1])[:200]})
                    continue
                problems.append(f"{run}: detected site {key} neither annotated nor ignored")
            # item D
            sp = os.path.join(rd, "strength.json")
            if rj.get("case") == "ticket-assignment" and os.path.exists(sp):
                sj = json.load(open(sp))
                d = sj.get("defects", {})
                entry["defects"] = {}
                for name in DEFECTS:
                    v = d.get(name)
                    entry["defects"][name] = None if v is None else {"caught": v.get("caught"), "by": v.get("by")}
            elif rj.get("case") == "ticket-assignment":
                entry["defects"] = "no strength.json"
            entry["item_launch"] = launch_kinds(rd, texts, {a for a, _ in ann.IGN.get(run, []) if a.startswith("run")})
            census.append(entry)
        scanned[root] = (n_run, n_acc)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  ", p)
    if check:
        return
    os.makedirs(OUT, exist_ok=True)
    json.dump(census, open(os.path.join(OUT, "census.json"), "w"), indent=1)
    write_txt(census, scanned)


def fam(model):
    m = (model or "").lower()
    if "sol" in m:
        return "sol"
    if "sonnet" in m:
        return "sonnet"
    return "other"


def agg(vals):
    vs = set(vals)
    return "yes" if vs == {"yes"} else "no" if vs == {"no"} else ("mixed" if vs else "-")


def write_txt(census, scanned):
    L = []
    L.append("Census of nested test runs in acceptance suites (mechanical: counts and quotes, no interpretation)")
    L.append("")
    L.append("Unit: a nested run is one call (spawn/exec/spawnSync/... or a thin wrapper around one) whose argument list starts another test run (`npm ... test`, or node with `--test`).")
    L.append("A call inside a shared helper function is listed once per call site, and its 'test' field lists each test that reaches it.")
    L.append("Dropping column: yes = every nested run in the suite removes NODE_TEST_CONTEXT from the child env (delete / undefined / rest-destructure / allow-list env), no = every one keeps it, mixed = some of each.")
    L.append("Evidence column: yes = the test requires a count/summary/named-test line from the child's output, no = exit status only (or output not inspected), mixed = per use.")
    L.append("")
    L.append("Scanned run folders (run.json and work/ present) per root, and how many had work/acceptance/:")
    for r, (a, b) in scanned.items():
        L.append(f"  {r}: {a} folders, {b} with acceptance")
    L.append(f"  total: {sum(a for a, _ in scanned.values())} folders, {sum(b for _, b in scanned.values())} with acceptance")
    L.append("")
    L.append("(1) One row per run")
    L.append("root | run | case | model effort | enrich | nested runs (call sites/test uses) | dropping the variable | requiring evidence | ticket-assignment defects caught by (default-limit-changed ; resolved-template-replaced ; audit-not-saved) | (extra) how ratchet/acceptance.json launches the items")
    rows = []
    for e in census:
        nr = e["nested_runs"]
        sites = {(n["file"], n["line"], n["call"]) for n in nr}
        drop = agg([n["env_drops_NODE_TEST_CONTEXT"] for n in nr])
        evd = agg([n["requires_evidence"] for n in nr])
        # per-site drop (a site's drop is the same for all uses)
        dd = {}
        for n in nr:
            dd[(n["file"], n["line"], n["call"])] = n["env_drops_NODE_TEST_CONTEXT"]
        drop = agg(list(dd.values()))
        d = e.get("defects")
        if isinstance(d, dict):
            ds = " ; ".join(("missed" if not v else ("missed" if not v["caught"] else "caught by " + ",".join(v["by"] or []))) if v is not None else "n/a" for v in (d[k] for k in DEFECTS))
        elif d:
            ds = d
        else:
            ds = ""
        rt = e["root"].split("-")[1]
        il = e.get("item_launch")
        ils = "; ".join(f"{k} x{v}" for k, v in sorted(il.items(), key=lambda kv: -kv[1])[:3]) if il else "no acceptance.json"
        rows.append(f"{rt} | {e['run']} | {e['case']} | {e['model']} {e['effort']} | {e['enrich']} | {len(sites)}/{len(nr)} | {drop} | {evd} | {ds} | items launched as: {ils}")
    L += rows
    L.append("")
    # totals
    L.append("(2) Totals by model family")
    fams = {"sol": [], "sonnet": [], "other": []}
    for e in census:
        fams[fam(e["model"])].append(e)
    def suite_stats(es):
        out = dict(suites=len(es), with_nested=0, any_keep=0, all_keep=0, any_keep_no_evidence=0)
        for e in es:
            nr = e["nested_runs"]
            if not nr:
                continue
            out["with_nested"] += 1
            keeps = [n for n in nr if n["env_drops_NODE_TEST_CONTEXT"] != "yes"]
            if keeps:
                out["any_keep"] += 1
            if len(keeps) == len(nr):
                out["all_keep"] += 1
            if any(n["requires_evidence"] == "no" for n in keeps):
                out["any_keep_no_evidence"] += 1
        return out
    models = {}
    for e in census:
        models.setdefault(fam(e["model"]), set()).add(e["model"])
    hdr = "family (models) | suites counted | suites with >=1 nested run | suites with >=1 nested run that keeps the variable | suites where every nested run keeps the variable | suites with >=1 nested run that keeps the variable and requires no evidence"
    L.append(hdr)
    tot = suite_stats(census)
    for k in ("sol", "sonnet", "other"):
        s = suite_stats(fams[k])
        L.append(f"{k} ({', '.join(sorted(models.get(k, [])))}) | {s['suites']} | {s['with_nested']} | {s['any_keep']} | {s['all_keep']} | {s['any_keep_no_evidence']}")
    L.append(f"all | {tot['suites']} | {tot['with_nested']} | {tot['any_keep']} | {tot['all_keep']} | {tot['any_keep_no_evidence']}")
    L.append("")
    L.append("Counting rule for the last column: among that suite's nested runs that keep the variable, at least one has a test use with no evidence requirement (exit status only, or output not inspected).")
    L.append("")
    # (3) unclear
    L.append("(3) Unclear cases (drop = unclear)")
    un = [(e, n) for e in census for n in e["nested_runs"] if n["env_drops_NODE_TEST_CONTEXT"] == "unclear"]
    if not un:
        L.append("  none")
    for e, n in un:
        L.append(f"  {e['run']} {n['file']}:{n['line']}: {n['env_note']}")
    L.append("")
    L.append("Appendix A. Nested runs, per use")
    for e in census:
        L.append(f"## {e['root']} / {e['run']}  case={e['case']} model={e['model']} effort={e['effort']} enrich={e['enrich']} preserve={e['preserve']}")
        for n in e["nested_runs"]:
            ra = n["file_run_as"]
            L.append(f"- {n['file']}:{n['line']} test={n['test']} (nearest preceding test start: {n['enclosing_test_title_nearest_preceding']!r}) drop={n['env_drops_NODE_TEST_CONTEXT']} evidence={n['requires_evidence']}" + (f" file_run_as={ra}" if ra else ""))
            L.append(f"    call: {n['call']}")
            L.append(f"    env: {n['env_note']}")
            L.append(f"    evidence: {n['evidence_quote']}")
        for g in e["ignored_runner_calls"]:
            L.append(f"- (not counted: runner script or non-run call) {g['file']}:{g['line']}: {g['call']}")
    open(os.path.join(OUT, "census.txt"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
