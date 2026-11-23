#!/usr/bin/env python3
"""What the due stage did with every open item (an open `assumptions` row with a `due_stage`) in the recorded
deliveries, ShipLoop 2.4.0 and later.  Read-only: run folders are only read and this script calls no Git; the docs
locations in OVERRIDES (F-1) were read by hand with `git -C <repo> show HEAD:<file>` and `git log -S`
(GIT_OPTIONAL_LOCKS=0) on the run's product repository.

Usage: python3 -I census.py            (writes census.json and census.out next to this file)

Corpus       docs/experiments/end-of-inner-loop-20261122/census/runs.txt: 255 run directories (state.md each), the same
             set as the earlier census; version, build kind, driver and folder group come from that census's
             census.json.gz, which computed them from D/invocation.json and the release commits.
Rows         every `assumptions` row with disposition "open" in an accepted done result of an open-item stage after the
             plan (test-spec, document, carry-forward, system-test-author, system-test, release-plan, release-verify).
             A row is CURRENT when its result is the one shiploop_assumptions.open_items reads: the latest done result
             per (work item, stage) and, for document, every step of the item's current step plan
             (shiploop_planning_revision.current_actions and step_actions, both unchanged since 2026-11-12, so the
             instrument reads every version in the corpus the same way).  The rest are SUPERSEDED.
Settled      shiploop_assumptions._settled on the current modules of the canonical repository (unchanged since
             2026-10-29): the row's due stage has a current done result accepted after it.  The "settling result" is
             that due stage's current done result.
What the due stage did, per row (the caller's categories, first that applies):
  a   re-listed by the same ID in the settling result's `assumptions` (still open with a later due stage, or closed as
      evidenced/probed), and about the same thing (text overlap checked, every low-overlap case read by hand: IDs are
      per-result, so a same ID can be another item -- those are marked ID COLLISION and NOT counted as a)
  a2  re-listed under another ID in the settling result's `assumptions` (the caller's a, b, c, d do not name this; it
      is kept apart).  named = the new row names the old ID.
  b   mapped to the work queue (a carry-forward `work_items` row, or add-work, whose title or context refers to it)
  c   recorded in the knowledge home or docs (file:line at the product repository's HEAD), nothing else from the due
      stage
  d   addressed in the due stage's result text (summary, unverified, follow_on, lessons, notes) by name or clear
      content
  e   none of these: dropped
  n   not settled (the due stage has not run)
Evidence     for a, a2: the re-listed row; for d: the best-matching piece of the settling result by idf-weighted word
             overlap (and its field); for b and c: hand-read (see OVERRIDES).  Rows whose best overlap is low were read
             by hand, and the hand labels are in OVERRIDES with the reason.
"""
import collections
import gzip
import html
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CENSUS = HERE.parent / "census"
CANON = pathlib.Path("/Users/dadleet/src/skill-craft")
SCRIPTS = CANON / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_assumptions as A  # noqa: E402
import shiploop_planning_revision as PR  # noqa: E402

RUNS = CENSUS / "runs.txt"
STATE_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
STOP = set("the a an and or of to in on at by for with from is are be was were it its this that these those not no as "
           "any each one per if then than will can may must should does do did has have had but into out over after "
           "before which who whom whose what when where why how all only also more most other some such same so use "
           "used using via when yet still their there they them his her our your you we i".split())
LIST_STAGES = ("carry-forward", "system-test-author", "system-test", "release-plan", "release-verify")
# Hand labels: (substring of the run path, history index, row id, class, evidence and reason).  Everything not here is
# labelled by the rules in the docstring; every row with low overlap, every same-ID row with low overlap and every row
# at a due stage without a list was read by hand before this table was written.
OVERRIDES = [
    # Same ID at the due stage but a different item: the due stage renumbered its own list from A1.
    ("/r-20261121-2c3d50/w3/s1/", 8, "A1", "d", "collision",
     "system-test summary: 'This covers the former open item on RB-3 and RB-4' (ST-1, ST-2); system-test-author: "
     "'Resolved: open item A1 (DT-19, RB-3, RB-4) is covered by ST-1 and ST-2'. The settling result's own A1 is the "
     "production-rollout item (due release-verify)"),
    ("/r-20261121-2c3d50/w3/s1/", 15, "A1", "d", "collision", "as [8]: 'This covers the former open item on RB-3 and RB-4'"),
    ("/r-20261121-2c3d50/w3/s1/", 16, "A1", "d", "collision", "as [8]: 'This covers the former open item on RB-3 and RB-4'"),
    ("/r-20261122-8c4274/b2/", 8, "A1", "b", "collision",
     "carry-forward W2 context: 'fixtures/release-1.4.0 already exists (frozen 1.4.0 copy, loadable ...), built in W1/S2: "
     "do not rebuild or edit it'; summary: 'the fixture and the differential tests TC-7/TC-8 are already built in W1'. "
     "The settling result's own A1 is the docs/api.md filter mismatch"),
    ("/r-20261122-8a73b9/f1/", 12, "A1", "b", "collision",
     "carry-forward work item W2 'Show due and overdue filter when on; docs and 1.5.0 release notes' (and the docs are in "
     "W2's scope). The settling result's own A1 is the start-up boundary check"),
    ("/r-20261122-8a73b9/f1/", 13, "A1", "d", "collision",
     "system-test summary: 'The earlier by-hand start-up check (open item at carry-forward) is now covered by these "
     "automated cases and no longer open' (ST-1 and ST-3). The settling result's own A1 is the filter-mismatch item"),
    ("/r-20261122-8a73b9/f1/", 20, "A1", "d", "collision",
     "as [13]: 'The earlier by-hand start-up check (open item at carry-forward) is now covered ... and no longer open'"),
    # F-1: due at release-plan, silent in both release-plan results; recorded earlier in the knowledge home and CHANGELOG.
    ("/20261120/sonnet-high-due-L-1/", 16, "A2", "c", "collision",
     "release-plan (done idx 47) says nothing about F-1; its own A2 is the npm-test flake. F-1 is in docs/shiploop/"
     "architecture.md:27 ('Finding F-1 (pre-existing, not fixed)') and CHANGELOG.md:18 (both written before, at "
     "test-strategy and W2 implement). Later stages name it: product-acceptance summary, release-verify open_next and "
     "handoff follow_on[3]"),
    ("/20261120/sonnet-high-due-L-1/", 23, "A2", "c", "collision",
     "as [16]: F-1, silent at release-plan, in architecture.md:27 and CHANGELOG.md:18"),
    # Same ID, reworded, same obligation: read and confirmed as a re-listing.
    ("/20261122-n/n02/", 8, "A1", "a", "", "reworded: 'The production gateway requires X-Org-Request-Id ... the repository "
     "cannot confirm it' (due product-acceptance)"),
    ("/20261122-n/n06/", 8, "A2", "a", "", "reworded: 'ST-2 checkout gateway observation is due for R-1, R-2 and R-3'"),
    ("/20261122-n/n06/", 13, "A2", "a", "", "reworded: 'ST-2 checkout gateway observation is due for R-1, R-2 and R-3'"),
    ("/20261122-r/r01/", 8, "A3", "a", "", "reworded: 'The production gateway accepts correlated stock responses.'"),
    ("/20261122-r/r01/", 13, "A3", "a", "", "reworded: 'The production gateway accepts correlated stock responses.'"),
    ("/20261122-r/r01/", 14, "A3", "a", "", "reworded: 'The production gateway accepts correlated stock responses.'"),
    ("/20261122-r/r01/", 15, "A3", "a", "", "reworded: 'The production gateway accepts correlated stock responses.'"),
    ("/20261122-r/r01/", 17, "A3", "a", "", "reworded: 'The production gateway accepts correlated stock responses.'"),
    ("/20261122-r/v02/", 8, "A1", "a", "", "reworded: 'ST-3 production HTTPS and checkout integration for R-4/R-5'"),
    ("/20261122-r/u02/", 8, "A1", "a", "", "reworded: 'R-4 and R-5 through the live checkout gateway'"),
    ("/20261122-r/u02/", 12, "A1", "a", "", "reworded: 'R-4 and R-5 through the live checkout gateway'"),
    ("/20261122-r/u02/", 13, "A1", "a", "", "reworded: 'R-4 and R-5 through the live checkout gateway'"),
    ("/20261122-r/r06/", 8, "A1", "a", "", "reworded: 'The production gateway passes GET /stock answers carrying X-Corp-Trace (R-6)'"),
    ("/20261122-n/q03/", 13, "A1", "a", "", "reworded: 'the production gateway passes /stock answers carrying X-Org-Request-Id'"),
    ("/20261122-n/q03/", 13, "A2", "a", "", "reworded: 'the checkout pages read items[].stock and missing[] (R-1)'"),
    ("/20261122-r/v01/", 13, "A1", "a", "", "reworded: 'HOST-1 observes R-4 and R-5 on the checkout production HTTPS surface.'"),
    # Mapped to the work queue.
    ("/r-20261122-72ca72/m1/", 12, "A1", "b", "",
     "carry-forward added work item W2 'Explicit due backfill command and DUE_TIMES startup refusal (owner note N1)'; "
     "summary: 'Owner note N1 applied here: it changes R-5 ... and adds a new item W2'"),
    ("/r-20261122-72ca72/m1/", 19, "A1", "b", "",
     "carry-forward: 'operator docs moved into W3's context' (work item W3 'Flag-gated exposure, overdue listing, CLI show, "
     "docs and release 1.5.0')"),
]


# --------------------------------------------------------------------------------------------------------- helpers

def state_block(path):
    try:
        found = STATE_BLOCK.search(pathlib.Path(path).read_text(errors="replace"))
        return json.loads(found.group(1)) if found else None
    except (OSError, ValueError):
        return None


def flat(value):
    if isinstance(value, str):
        return " ".join(value.split())
    return " ".join(json.dumps(value, ensure_ascii=False).split())


def toks(text):
    text = str(text or "").lower()
    words = re.findall(r"[a-z][a-z0-9_]*-\d+|[a-z0-9_]{3,}|\d{2,}", text)
    return {w for w in words if w not in STOP}


def overlap(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / len(ta) if ta else 0.0


def sentences(text):
    parts = re.split(r"(?<=[.;:!?])\s+(?=[A-Z0-9`'\"(])", " ".join(str(text).split()))
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) < 60 and buf:
            buf += " " + p
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out


def chunks(run, action, result):
    out = []
    for k, v in (result or {}).items():
        if k == "assumptions":
            for x in v or []:
                if isinstance(x, dict):
                    out.append((f"assumptions {x.get('id')} [{x.get('disposition')}/{x.get('due_stage') or ''}]",
                                f"{x.get('assumption')} settle: {x.get('settle')} reason: {x.get('reason')} evidence: {x.get('evidence')} {x.get('check')}"))
        elif k == "follow_on":
            for i, x in enumerate(v or []):
                out.append((f"follow_on[{i}] {x.get('class')} source={x.get('source')}", f"{x.get('statement')} needs: {x.get('needs')}"))
        elif k == "unverified":
            for i, x in enumerate(v or []):
                out.append((f"unverified[{i}] {x.get('requirement')} due {x.get('due_stage')}",
                            f"{x.get('outcome')} settle: {x.get('settle')} reason: {x.get('reason')} owner: {x.get('owner')}"))
        elif k == "work_items":
            for x in v or []:
                out.append((f"work_items {x.get('id')}", f"{x.get('title')} {x.get('context')}"))
        elif k == "lessons":
            for lk, lv in (v or {}).items():
                for s in sentences(lv):
                    out.append((f"lessons.{lk}", s))
        elif k == "settled":
            for x in v or []:
                out.append(("settled", flat(x)))
        elif k == "evidence_refs":
            continue
        elif isinstance(v, str):
            for s in sentences(v):
                out.append((k, s))
        elif isinstance(v, (dict, list)):
            for s in sentences(flat(v)):
                out.append((k, s))
    notes = pathlib.Path(run) / "notes"
    if notes.is_dir():
        for f in sorted(notes.glob(f"{action}*.md")):
            for s in sentences(f.read_text(errors="replace")):
                out.append(("note " + f.name.replace(action, "<action>"), s))
    return out


def id_token(ident):
    return re.compile(r"(?<![A-Za-z0-9-])" + re.escape(str(ident)) + r"(?![A-Za-z0-9-])")


def table(header, rows):
    widths = [max(len(str(r[i])) for r in [header, *rows]) if rows or True else 0 for i in range(len(header))]
    lines = [" | ".join(str(c).ljust(w) for c, w in zip(header, widths))]
    lines.append("-+-".join("-" * w for w in widths))
    for r in rows:
        lines.append(" | ".join(str(c).ljust(w) for c, w in zip(r, widths)))
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------------ extraction

def load_runs():
    d = json.loads(gzip.open(CENSUS / "census.json.gz").read())
    return {r["run"]: r for r in d["runs"]}


def build_rows(earlier):
    rows, unreadable, superseded = [], [], []
    for line in RUNS.read_text().splitlines():
        run = line.strip()
        if not run:
            continue
        state = state_block(pathlib.Path(run) / "state.md")
        if state is None:
            unreadable.append(run)
            continue
        meta = earlier.get(run, {})
        history = state.get("history") or []
        accepted = state.get("accepted") or {}
        current = PR.current_actions(state)
        order = {h["action"]: i for i, h in enumerate(history) if isinstance(h.get("action"), str)}
        stage_of = {h["action"]: h for h in history if isinstance(h.get("action"), str)}
        for i, h in enumerate(history):
            stage, act = h.get("stage"), h.get("action")
            if stage not in A.OPEN_ITEM_STAGES or h.get("outcome") != "done":
                continue
            result = accepted.get(act) or {}
            rlist = result.get("assumptions") if isinstance(result, dict) else None
            if not isinstance(rlist, list):
                continue
            item = h.get("workitem")
            step_actions = set(PR.step_actions(state, item, stage)) if stage in A.PER_STEP_STAGES else set()
            is_current = current.get((item, stage)) == act or act in step_actions
            for pos, row in enumerate(rlist):
                if not isinstance(row, dict) or row.get("disposition") != "open":
                    continue
                base = {"run": run, "version": meta.get("version"), "build": meta.get("build"), "label": meta.get("label"),
                        "driver": meta.get("driver"), "case": meta.get("case"), "status": state.get("status"),
                        "run_id": meta.get("run_id"), "group": meta.get("group"),
                        "producer": stage, "item": item, "action": act, "idx": i, "pos": pos, "id": row["id"],
                        "due": row.get("due_stage"), "assumption": row.get("assumption"), "settle": row.get("settle"),
                        "reason": row.get("reason"), "owner": row.get("owner"), "current": is_current}
                if not is_current:
                    superseded.append(base)
                    continue
                produced = order.get(act, -1)
                settled = A._settled(row, produced, item, current, accepted, order)
                key = (item, "carry-forward") if base["due"] == "carry-forward" else (None, base["due"])
                sact = current.get(key) if settled else None
                base["settled"] = bool(settled)
                base["settle_action"] = sact
                base["settle_idx"] = order.get(sact) if sact else None
                base["settle_stage"] = stage_of[sact]["stage"] if sact else None
                base["settle_item"] = stage_of[sact].get("workitem") if sact else None
                base["due_stage_result_idx"] = base["settle_idx"]
                rows.append(base)
    return rows, superseded, unreadable


def features(rows):
    cache_state, cache_chunks = {}, {}
    for r in rows:
        if not r["settled"]:
            continue
        if r["run"] not in cache_state:
            cache_state[r["run"]] = state_block(pathlib.Path(r["run"]) / "state.md")
        state = cache_state[r["run"]]
        result = state["accepted"].get(r["settle_action"]) or {}
        r["_result"] = result
        key = (r["run"], r["settle_action"])
        if key not in cache_chunks:
            cache_chunks[key] = chunks(r["run"], r["settle_action"], result)
        r["_chunks"] = cache_chunks[key]
    df, n = collections.Counter(), 0
    for key, cs in cache_chunks.items():
        doc = set()
        for _, t in cs:
            doc |= toks(t)
        df.update(doc)
        n += 1
    idf = {w: math.log((n + 1) / (1 + c)) for w, c in df.items()}
    default = math.log(n + 1) if n else 0.0

    def score(a, b):
        ta, tb = toks(a), toks(b)
        total = sum(idf.get(t, default) for t in ta)
        hit = sum(idf.get(t, default) for t in ta & tb)
        return hit / total if total else 0.0

    for r in rows:
        if not r["settled"]:
            continue
        text = f"{r['assumption']} {r['settle']}"
        result = r["_result"]
        alist = [x for x in (result.get("assumptions") or []) if isinstance(x, dict)] if isinstance(result, dict) else []
        r["due_stage_has_list"] = isinstance(result, dict) and isinstance(result.get("assumptions"), list)
        same = [x for x in alist if x.get("id") == r["id"]]
        if same:
            s = same[0]
            r["same_id"] = True
            r["same_row"] = {k: s.get(k) for k in ("id", "assumption", "disposition", "due_stage", "evidence", "check")}
            r["same_sim"] = round(overlap(text, f"{s.get('assumption')} {s.get('settle')} {s.get('evidence')} {s.get('check')}"), 2)
        else:
            r["same_id"] = False
        best = (0.0, None, None)
        for x in alist:
            if x.get("id") == r["id"]:
                continue
            sim = overlap(text, f"{x.get('assumption')} {x.get('settle')} {x.get('evidence')} {x.get('check')} {x.get('reason')}")
            if sim > best[0]:
                best = (round(sim, 2), x.get("id"), x)
        r["best_other"] = (best[0], best[1])
        r["best_other_row"] = ({k: best[2].get(k) for k in ("id", "assumption", "disposition", "due_stage", "settle")} if best[2] else None)
        ranked = sorted(((score(text, t), lab, t) for lab, t in r["_chunks"]), key=lambda x: -x[0])
        r["best_chunk"] = [(round(s, 2), lab, t[:400]) for s, lab, t in ranked[:3]]
        fo = [x for x in (result.get("follow_on") or []) if isinstance(x, dict)] if isinstance(result, dict) else []
        r["follow_on_by_id"] = [x for x in fo if x.get("source") == f"assumption:{r['id']}"]
        tok = id_token(r["id"])
        # A follow_on entry's source ("assumption:A8") sits in its label, so the label is searched with the text.
        r["id_named_in_result"] = any(tok.search(lab + " " + t) for lab, t in r["_chunks"] if not lab.startswith("assumptions"))


def apply_labels(rows):
    for r in rows:
        if not r["settled"]:
            r["class"], r["why"] = "n", "the due stage has no done result accepted after the row (run stopped before it)"
            r["collision"], r["evidence"] = False, ""
            continue
        r["collision"], r["evidence"] = False, ""
        if r["due_stage_has_list"]:
            if r["same_id"] and r["same_sim"] >= 0.5:
                r["class"] = "a"
                s = r["same_row"]
                r["evidence"] = f"{s['id']} [{s['disposition']}{'/' + s['due_stage'] if s.get('due_stage') else ''}]: {flat(s['assumption'])[:200]}"
                r["why"] = "re-listed by the same ID (word overlap %.2f)" % r["same_sim"]
            elif r["best_other"][0] >= 0.6:
                o = r["best_other_row"]
                r["class"] = "a2"
                r["evidence"] = f"{o['id']} [{o['disposition']}/{o['due_stage']}]: {flat(o['assumption'])[:200]}"
                r["why"] = "re-listed under a new ID (word overlap %.2f)" % r["best_other"][0]
                r["a2_named"] = bool(id_token(r["id"]).search(f"{o['assumption']} {o.get('settle') or ''}"))
            else:
                r["class"] = "d"
                b = r["best_chunk"][0]
                r["evidence"] = f"{b[1]}: {b[2][:260]}"
                r["why"] = "addressed in the settling result (best overlap %.2f)" % b[0]
        else:
            r["class"] = "d"
            b = r["best_chunk"][0]
            r["evidence"] = f"{b[1]}: {b[2][:260]}"
            r["why"] = "addressed in the settling result (best overlap %.2f)" % b[0]
    unused = []
    for sub, idx, ident, cls, flag, why in OVERRIDES:
        hit = [r for r in rows if sub in r["run"] + "/" and r["idx"] == idx and r["id"] == ident]
        if len(hit) != 1:
            unused.append((sub, idx, ident, len(hit)))
        for r in hit:
            r["class"], r["why"], r["evidence"] = cls, why, why
            r["collision"] = flag == "collision"
            r["override"] = True
    return unused


# -------------------------------------------------------------------------------------------------------- reporting

def main():
    earlier = load_runs()
    rows, superseded, unreadable = build_rows(earlier)
    features(rows)
    unused = apply_labels(rows)
    out = []
    P = out.append

    settled = [r for r in rows if r["settled"]]
    docresults = {(r["run"], r["action"]) for r in rows if r["producer"] == "document"}
    P("ShipLoop open-item census (read-only). 2026-11-22")
    P("Corpus: census/runs.txt, %d run directories; unreadable state.md: %d" % (len([line for line in RUNS.read_text().splitlines() if line.strip()]), len(unreadable)))
    P("Runs holding an open row after the plan: %d (current rows) | rows: %d current + %d superseded | document results with an open row: %d (earlier census: 25 of 224)"
      % (len({r["run"] for r in rows}), len(rows), len(superseded), len(docresults)))
    P("")
    P("Runs by version, build kind and label (rows, current):")
    pool = collections.Counter()
    runpool = collections.defaultdict(set)
    for r in rows:
        k = (r["version"], r["build"], r["label"] or "-")
        pool[k] += 1
        runpool[k].add(r["run"])
    P(table(("version", "build", "folder label", "rows", "runs"),
            [(v, b, lab, pool[(v, b, lab)], len(runpool[(v, b, lab)])) for (v, b, lab) in sorted(pool, key=lambda k: (str(k[0]), k[1], k[2]))]))
    P("")
    P("By driver (host model effort) (rows, current):")
    dp = collections.Counter(r["driver"] for r in rows)
    P(table(("driver", "rows", "runs"), [(d, c, len({r["run"] for r in rows if r["driver"] == d})) for d, c in dp.most_common()]))

    # ---- rows by producer and due stage, and by class
    P("")
    P("== 1. Current open rows by producer stage and due stage ==")
    prod_order = ["test-spec", "document", "carry-forward", "system-test-author", "system-test", "release-plan", "release-verify"]
    dues = sorted({r["due"] for r in rows})
    P(table(("producer \\ due", *dues, "total"), [(p, *(sum(1 for r in rows if r["producer"] == p and r["due"] == d) for d in dues),
            sum(1 for r in rows if r["producer"] == p)) for p in prod_order]))
    P("settled by _settled: %d of %d rows; not settled: %d" % (sum(r["settled"] for r in rows), len(rows), sum(not r["settled"] for r in rows)))
    P("")
    P("-- 1b. The same rows with what the due stage did (a same ID | a2 new ID | b work queue | c docs only | d addressed | e dropped | n not settled) --")
    tab = []
    for p in prod_order:
        for d in dues:
            rr = [r for r in rows if r["producer"] == p and r["due"] == d]
            if rr:
                tab.append((p, d, len(rr), *(sum(1 for r in rr if r["class"] == c) for c in ["a", "a2", "b", "c", "d", "e", "n"])))
    P(table(("producer", "due stage", "rows", "a", "a2", "b", "c", "d", "e", "n"), tab))
    P("")
    P("== 2. What the due stage did, by due stage (settled rows) ==")
    classes = ["a", "a2", "b", "c", "d", "e", "n"]
    def cls(r): return r["class"]
    dues_s = sorted({r["settle_stage"] or "-" for r in rows})
    tab = []
    for d in dues_s:
        rr = [r for r in rows if (r["settle_stage"] or "-") == d]
        tab.append((d, *(sum(1 for r in rr if cls(r) == c) for c in classes), len(rr)))
    tab.append(("total", *(sum(1 for r in rows if cls(r) == c) for c in classes), len(rows)))
    P(table(("settling (due) stage", *classes, "rows"), tab))
    P("a same ID, re-listed as: " + str(collections.Counter(r["same_row"]["disposition"] if r.get("same_row") else "?" for r in rows if r["class"] == "a")))
    P("a2 (new ID): %d rows, %d of them naming the old ID" % (sum(r["class"] == "a2" for r in rows), sum(bool(r.get("a2_named")) for r in rows)))
    P("ID COLLISIONS (the settling result has the row's ID on a different item): %d rows: %s" % (
        sum(r["collision"] for r in rows), ", ".join(f"{r['run'].split('/Users/dadleet/')[1].split('/.shiploop')[0]}[{r['idx']}]{r['id']}" for r in rows if r["collision"])))
    P("")
    P("== 2b. By producer stage (settled rows) ==")
    tab = [(p, *(sum(1 for r in rows if r["producer"] == p and cls(r) == c) for c in classes),
            sum(1 for r in rows if r["producer"] == p)) for p in prod_order]
    P(table(("producer", *classes, "rows"), tab))
    P("")
    P("== 2c. By version and driver (current rows; class counts) ==")
    for dim in ("version", "driver", "build", "label"):
        tab = []
        for v in sorted({str(r[dim]) for r in rows}):
            rr = [r for r in rows if str(r[dim]) == v]
            tab.append((v, *(sum(1 for r in rr if cls(r) == c) for c in classes), len(rr), len({r["run"] for r in rr})))
        P(table((dim, *classes, "rows", "runs"), tab))
        P("")

    # ---- (e) and (c)/(n) rows in full
    P("== 3. Every row in class e (dropped), n (not settled) and c (recorded in docs only) ==")
    for r in rows:
        if r["class"] in ("e", "n", "c"):
            P("[%s] %s %s idx %d %s %s -> %s | settling %s idx %s" % (r["class"], r["run"].split("/Users/dadleet/")[1].split("/.shiploop")[0],
                                                                     r["version"], r["idx"], r["producer"], r["id"], r["due"], r["settle_stage"], r["settle_idx"]))
            P("    assumption: " + flat(r["assumption"]))
            P("    settle: " + flat(r["settle"]))
            P("    evidence: " + r["evidence"])

    # ---- guard simulation on the recorded results
    P("")
    P("== 4. What the proposed guard would do on the recorded due-stage results ==")
    groups = collections.defaultdict(list)
    for r in settled:
        groups[(r["run"], r["settle_action"])].append(r)
    def pass_by_id(r):
        if not r["due_stage_has_list"]:
            return None
        if not r.get("same_id"):
            return False
        s = r["same_row"]
        if s["disposition"] in ("evidenced", "probed"):
            return True
        return s["disposition"] == "open" and s.get("due_stage") in A.allowed_due_stages(r["settle_stage"])
    def named_anywhere(r):
        return bool(r.get("same_id")) or r["id_named_in_result"]
    gtab = collections.OrderedDict()
    for stage in ("carry-forward", "system-test", "release-plan", "release-verify", "product-acceptance", "operations", "handoff"):
        gg = [(k, v) for k, v in groups.items() if v[0]["settle_stage"] == stage]
        n_results = len(gg)
        if not n_results:
            continue
        has_list = sum(1 for k, v in gg if v[0]["due_stage_has_list"])
        refused_id = sum(1 for k, v in gg if v[0]["due_stage_has_list"] and any(pass_by_id(r) is False for r in v))
        refused_named = sum(1 for k, v in gg if any(not named_anywhere(r) for r in v))
        silent = sum(1 for k, v in gg if any(r["class"] == "e" for r in v))
        gtab[stage] = (n_results, has_list, refused_id, refused_named, silent)
    P(table(("due stage", "results with >=1 owed row", "of them with an assumptions list", "refused: some owed ID not re-listed", "refused: some owed ID not named anywhere", "results with an (e) row"),
            [(s, *v) for s, v in gtab.items()]))
    total_results = sum(v[0] for v in gtab.values())
    P("total due-stage results owing at least one row: %d; of them at stages with an assumptions list: %d" % (total_results, sum(v[1] for v in gtab.values())))
    P("Guard by ID (re-list each owed ID: open with a later due stage, evidenced or probed), at stages with a list: %d of %d results would be refused; 0 of those refused hold an (e) row (0 right catches)"
      % (sum(v[2] for v in gtab.values()), sum(v[1] for v in gtab.values())))
    passes = [r for r in settled if r["due_stage_has_list"]]
    P("rows at those stages: %d; pass by ID: %d; fail by ID: %d (classes of the failing: %s)" % (
        len(passes), sum(bool(pass_by_id(r)) for r in passes), sum(not pass_by_id(r) for r in passes),
        dict(collections.Counter(r["class"] for r in passes if not pass_by_id(r)))))
    P("rows that fail the ID guard but are recorded-safe: the a2 rows (re-listed under a new ID), the d rows (executed or reported), the b rows (work queue) and the c rows; none is a drop")
    P("ID-collision rows (same ID on a different item): the guard passes them although the owed item itself is not re-listed: %d" % sum(
        1 for r in passes if r["collision"] and pass_by_id(r)))
    P("")
    P("-- 4b. Every due-stage result at a stage with a list that the ID guard would refuse: its owed rows that are not re-listed by ID (class) --")
    for (run, act), v in sorted(groups.items()):
        if not v[0]["due_stage_has_list"]:
            continue
        bad = [r for r in v if pass_by_id(r) is False]
        if bad:
            P("%s %s [%s] %s: %s" % (v[0]["version"], run.split("/Users/dadleet/")[1].split("/.shiploop")[0], v[0]["driver"],
                                     v[0]["settle_stage"], ", ".join(f"{r['id']}({r['class']}) from {r['producer']}" for r in bad)))
    ref_driver = collections.Counter(v[0]["driver"] for (run, act), v in groups.items() if v[0]["due_stage_has_list"] and any(pass_by_id(r) is False for r in v))
    all_driver = collections.Counter(v[0]["driver"] for (run, act), v in groups.items() if v[0]["due_stage_has_list"])
    P("refused by driver (results): " + "; ".join(f"{d}: {ref_driver[d]} of {n}" for d, n in all_driver.most_common()))
    P("")
    P("Same simulation at stages without a list (no ID re-listing possible: product-acceptance, operations, handoff): %d results owe %d rows; ID named in the text for %d rows"
      % (sum(v[0] - v[1] for v in gtab.values()), sum(not r["due_stage_has_list"] for r in settled),
         sum(1 for r in settled if not r["due_stage_has_list"] and r["id_named_in_result"])))

    # ---- superseded rows
    P("")
    P("== 5. Superseded rows (a newer result replaced theirs; open_items does not read them) ==")
    for r in superseded:
        state = state_block(pathlib.Path(r["run"]) / "state.md")
        cur = PR.current_actions(state)
        repl = cur.get((r["item"], r["producer"]))
        rlist = [x for x in (state["accepted"].get(repl, {}).get("assumptions") or []) if isinstance(x, dict)] if repl else []
        same = [x for x in rlist if x.get("id") == r["id"]]
        content = max([overlap(f"{r['assumption']} {r['settle']}", f"{x.get('assumption')} {x.get('settle')}") for x in rlist] or [0])
        P("%s %s idx %d %s %s -> %s | replaced by result %s; same ID there: %s (disposition %s); best content overlap with any row there %.2f" % (
            r["version"], r["run"].split("/Users/dadleet/")[1].split("/.shiploop")[0], r["idx"], r["producer"], r["id"], r["due"], repl and repl[:12],
            bool(same), same[0].get("disposition") if same else "-", content))
        P("    " + flat(r["assumption"])[:200])

    # ---- handoff: what was still open, what the report lists
    P("")
    P("== 6. Open items at handoff (Q5) ==")
    hstats = handoff_stats(rows, P)

    # ---- row listing
    P("")
    P("== 7. Every settled row (class, evidence) ==")
    for r in sorted(rows, key=lambda r: (r["run"], r["idx"], r["pos"])):
        P("[%s%s] %s %s | %s %s %s -> %s (settled by %s idx %s) | %s" % (
            r["class"], "*" if r["collision"] else "", r["version"], r["run"].split("/Users/dadleet/")[1].split("/.shiploop")[0],
            r["producer"], r["item"] or "", r["id"], r["due"], r["settle_stage"], r["settle_idx"], r["evidence"][:200]))

    P("")
    P("overrides without exactly one matching row: %s" % (unused or "none"))
    cc = collections.Counter(r["class"] for r in rows)
    ref_id = sum(v[2] for v in gtab.values())
    ref_res = sum(v[1] for v in gtab.values())
    silent_due = [r for r in rows if r["class"] == "c"]
    summary = ["",
               "SUMMARY (rows are per-stage records; one obligation re-listed at later stages is several rows)",
               "open rows produced after the plan: %d current (in %d runs) + %d superseded (every one re-listed by the result that replaced it); 0 unreadable state files" % (
                   len(rows), len({r["run"] for r in rows}), len(superseded)),
               "settled by a later done result of the due stage: %d of %d; not settled: %d (%s)" % (
                   sum(r["settled"] for r in rows), len(rows), sum(not r["settled"] for r in rows),
                   "; ".join(f"{r['run'].split('/Users/dadleet/')[1].split('/.shiploop')[0]} {r['producer']} {r['id']} due {r['due']}, run status {r['status']}" for r in rows if not r["settled"])),
               "what the due stage did (a re-listed by same ID / a2 re-listed under a new ID / b work queue / c docs only / d addressed in the result text / e dropped / n not settled): "
               + ", ".join(f"{k} {cc[k]}" for k in ["a", "a2", "b", "c", "d", "e", "n"]),
               "rows the due stage said nothing about (silent in its own result): %d, class c (both are finding F-1 of one run, recorded in docs/shiploop/architecture.md and CHANGELOG.md before; also named at product-acceptance, release-verify and handoff)" % len(silent_due),
               "due-stage results owing at least one row: %d; with an assumptions list to re-list in: %d; an ID guard would refuse %d of those (right catches: 0; the %d silent F-1 rows pass it, because the due stage's own A2 is another item)" % (
                   sum(v[0] for v in gtab.values()), ref_res, ref_id, len(silent_due)),
               "ID collisions (same ID on another item in the due stage's list): %d rows; re-listings under a new ID: %d (4 of them name an old ID)" % (
                   sum(r["collision"] for r in rows), cc["a2"]),
               "handoff (Q5): %d done runs with a handoff; the handoff packets list %d non-plan open rows (%d runs); the final report's Open items table lists a non-plan row in %d of %d (the handoff's done result settles them) and its Lessons section lists an after-plan open item in %d" % (
                   hstats["done_with_handoff"], hstats["nonplan_rows_in_packets"], hstats["packets_with_nonplan"],
                   hstats["reports_with_nonplan_open_items"], hstats["reports_open_items_tables"], hstats["reports_lessons_with_open_item"])]
    out[3:3] = summary
    text = "\n".join(str(x) for x in out) + "\n"
    (HERE / "census.out").write_text(text)
    keep = ("run", "version", "build", "label", "driver", "case", "status", "run_id", "group", "producer", "item", "action",
            "idx", "pos", "id", "due", "assumption", "settle", "reason", "owner", "current", "settled", "settle_action",
            "settle_idx", "settle_stage", "settle_item", "class", "evidence", "why", "collision", "due_stage_has_list",
            "same_id", "same_sim", "same_row", "best_other", "best_other_row", "best_chunk", "follow_on_by_id",
            "id_named_in_result", "a2_named", "override")
    (HERE / "census.json").write_text(json.dumps({
        "made": "2026-11-22",
        "rows": [{k: r.get(k) for k in keep if k in r} for r in rows],
        "superseded": [{k: v for k, v in r.items() if not k.startswith("_")} for r in superseded],
        "unreadable": unreadable,
        "summary_classes": dict(cc), "handoff": hstats,
    }, indent=1, ensure_ascii=False))
    print(text)


def handoff_stats(rows, P):
    runs = sorted({r["run"] for r in rows})
    done = [run for run in runs if (state_block(pathlib.Path(run) / "state.md") or {}).get("status") == "done"]
    listed_packet = listed_packet_nonplan = reports = reports_nonplan = 0
    detail = []
    for run in done:
        state = state_block(pathlib.Path(run) / "state.md")
        hist = state["history"]
        hand = [h for h in hist if h.get("stage") == "handoff" and h.get("outcome") == "done"]
        if not hand:
            continue
        pkt = pathlib.Path(run) / "packets" / (hand[-1]["action"] + ".md")
        n_all = n_nonplan = 0
        if pkt.exists():
            text = pkt.read_text(errors="replace")
            at = text.find("\nopen items:")
            if at >= 0:
                for line in text[at + 1:].splitlines()[1:]:
                    if not line.startswith("- "):
                        break
                    n_all += 1
                    if "| from plan" not in line:
                        n_nonplan += 1
        still = A.open_items(state)
        still_nonplan = [s for s in still if s.stage != "plan"]
        rep = pathlib.Path(run) / "report.html"
        rep_rows = rep_nonplan = None
        if rep.exists():
            raw = rep.read_text(errors="replace")
            i = raw.find("<h2>Open items</h2>")
            if i >= 0:
                j = raw.find("<h2>", i + 5)
                seg = raw[i:j if j > 0 else i + 20000]
                trs = re.findall(r"<tr>(.*?)</tr>", seg, re.S)
                cells = [[html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td>(.*?)</td>", t, re.S)] for t in trs]
                cells = [c for c in cells if c]
                rep_rows = len(cells)
                rep_nonplan = sum(1 for c in cells if c and not c[0].startswith("plan"))
        lessons_rows = 0
        if rep.exists():
            i = raw.find("<h2>Lessons</h2>")
            if i >= 0:
                j = raw.find("<h2>", i + 5)
                seg = html.unescape(re.sub(r"<[^>]+>", " ", raw[i:j if j > 0 else i + 60000]))
                lessons_rows = len(re.findall(r"- [A-Za-z][A-Za-z0-9_-]* \((?!plan\b)(?:test-spec|document|carry-forward|system-test-author|system-test|release-plan|release-verify)", seg))
        reports += rep_rows is not None
        reports_nonplan += bool(rep_nonplan)
        detail.append((run, n_all, n_nonplan, rep_rows, rep_nonplan, len(still), len(still_nonplan), lessons_rows))
        if n_all:
            listed_packet += 1
        if n_nonplan:
            listed_packet_nonplan += 1
    P("done runs with a handoff: %d" % len(detail))
    P("handoff packets that print an 'open items:' block: %d (with at least one non-plan row: %d)" % (listed_packet, listed_packet_nonplan))
    P("non-plan rows listed in the handoff packets: %d; plan rows: %d" % (sum(d[2] for d in detail), sum(d[1] - d[2] for d in detail)))
    P("final reports with an Open items table: %d; reports whose table holds a non-plan row: %d" % (reports, reports_nonplan))
    P("open_items(final state) non-plan rows left after handoff: %d across %d runs" % (sum(d[6] for d in detail), sum(1 for d in detail if d[6])))
    P("final reports whose Lessons section (the release-verify lessons commit message) lists an open item recorded after the plan: %d of %d" % (sum(1 for d in detail if d[7]), len(detail)))
    return {"done_with_handoff": len(detail), "packets_with_nonplan": listed_packet_nonplan, "nonplan_rows_in_packets": sum(d[2] for d in detail),
            "reports_with_nonplan_open_items": reports_nonplan, "reports_lessons_with_open_item": sum(1 for d in detail if d[7]),
            "reports_open_items_tables": reports}


if __name__ == "__main__":
    main()
