#!/usr/bin/env python3
"""real_table.py: the tables and the predictions for E17 (the real repository), from the exported evidence.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A14, journal entry E17). Reads evidence/e17-<host>-<cell>/
(score.json, ledger.jsonl, invocation.json). The cells, per host:

  s    one context does the three features in turn in one checkout (the control)
  qs   fresh sub-agents one at a time (capacity one), a worktree each, the re-test after each merge: the same workflow as q0 without the concurrency
  q0   fresh sub-agents three at a time, a worktree each, the re-test after each merge, the fix rule, no landing
  qp   q0 and the teammate's change landing on main (a rename the new tests and code did not know)
  qr   qp with the redo rule (E13's: abort and offer the task again from main's current head)

A comparison is made only between trials that are both valid and compliant (the treatment happened: s ran in one context with no sub-agent, qs
had at least three fresh agents and never more than one attempt at a time, q0 qp qr had at least three agents and at least two attempts at once;
every trial exited on its own and ran the requested model and effort). Otherwise it is printed as "n/c" and counts as inconclusive.

  python3 real_table.py            the tables, the ratios, R16, R16b, R17, R18 and the predictions P70 to P84 where the cells exist
  python3 real_table.py --json     the points as JSON
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
EV = Path(os.environ.get("PPE_EVIDENCE", HERE / "evidence"))
HOSTS = ("claude", "grok", "codex")
CELLS = ("s", "qs", "q0", "qp", "qr")
PROFILE = {"claude": ("claude-sonnet-5-5", "high"), "grok": ("grok-4.6", "xhigh"), "codex": ("gpt-6.1-sol", "medium")}


def name(host: str, cell: str) -> str:
    return f"e17-{host}-{cell}"


def have(host: str, cell: str) -> bool:
    return (EV / name(host, cell) / "score.json").is_file()


def load(host: str, cell: str) -> dict:
    d = EV / name(host, cell)
    m = json.loads((d / "score.json").read_text())
    inv = json.loads((d / "invocation.json").read_text())
    ledger = [json.loads(line) for line in (d / "ledger.jsonl").read_text().splitlines() if line.strip()]
    w = m.get("write") or {}
    o = w.get("oracle") or {}
    tok = m.get("tokens") or {}
    native = m.get("native") or {}
    kind = (m.get("mechanism") or {}).get("kind")
    peak = w.get("attempt_peak")
    if cell == "s":
        compliant = native.get("agents") == 0 and kind in ("parent-executed", "serial")
    elif cell == "qs":
        compliant = (native.get("agents") or 0) >= 3 and peak == 1
    else:
        compliant = (native.get("agents") or 0) >= 3 and (peak or 0) >= 2
    compliant = bool(compliant and inv.get("status") == "exited" and (inv.get("model"), inv.get("effort")) == PROFILE[host])
    landed_seq = next((e["seq"] for e in ledger if e["kind"] == "landed"), None)
    after = [e for e in ledger if landed_seq and e["seq"] > landed_seq and e["kind"] in ("merged", "conflict", "redtest")]
    retests = [e["detail"]["seconds"] for e in ledger if e["kind"] == "retest" and not e["detail"].get("landing")]
    return {"name": name(host, cell), "host": host, "cell": cell, "score": m, "whole": (m.get("timings") or {}).get("launch_to_exit_s"),
            "valid": bool(m.get("valid")), "compliant": compliant, "write": w, "oracle": o, "attempt_s": w.get("attempt_s") or {},
            "tokens": tok.get("input_all"), "output": tok.get("output_all"), "cost": tok.get("cost_usd"),
            "tokens_complete": not tok.get("children_without_usage"), "load": (inv.get("loadavg") or [None])[0],
            "first_after_landing": after[0]["kind"] if after else None, "median_retest_s": statistics.median(retests) if retests else None, "retests": retests, "ledger": ledger, "launched": inv.get("started"),
            "integration_failures": sum(1 for e in ledger if e["kind"] in ("conflict", "redtest")),
            "mergefails": sum(1 for e in ledger if e["kind"] == "mergefail")}


def fmt(x, nd=1):
    return "n/a" if x is None else (f"{x:,.{nd}f}" if isinstance(x, float) else f"{x:,}")


def ok(*trials) -> bool:
    return all(t and t["valid"] and t["compliant"] for t in trials) and all(t["whole"] for t in trials)


def table(data: dict) -> None:
    print("E17: three real features on a real service (whole run in seconds; tokens and cost over all contexts)\n")
    print(f"{'host':<7}{'cell':<5}{'whole':>8}{'rnd 1':>8}{'slowest':>9}{'valid':>7}{'compl':>7}{'merge':>6}{'confl':>6}{'red':>4}{'retry':>6}{'fix':>4}{'kit s':>7}{'retest':>7}{'input tok':>13}{'cost':>8}{'load':>6}")
    for h in HOSTS:
        for c in CELLS:
            if (h, c) not in data:
                continue
            d = data[(h, c)]
            w = d["write"]
            toks = fmt(d["tokens"]) + ("" if d["tokens_complete"] else "*")
            print(f"{h:<7}{c:<5}{fmt(d['whole']):>8}{fmt(w.get('first_round_s')):>8}{fmt(w.get('slowest_first_s')):>9}{str(d['valid']):>7}{str(d['compliant']):>7}{fmt(w.get('merges')):>6}"
                  f"{fmt(w.get('conflicts')):>6}{fmt(w.get('redtests')):>4}{fmt(w.get('retries')):>6}{fmt(w.get('fix_attempts')):>4}{fmt(w.get('kit_total_s')):>7}{fmt(d['median_retest_s']):>7}{toks:>13}{fmt(d['cost'], 2):>8}{fmt(d['load']):>6}")
    print("  (* = a child has no usage record, so the total is incomplete)")
    print("\nThe oracle: per feature the behavior checks on the final tree / on the first branch alone (interference = alone passes, final fails); the whole tree's own-tests checks;")
    print("            I1-I5 ('.' pass, 'X' fail); the final suite; what the re-test decided on each attempted integration, judged offline against the features' behavior")
    print(f"{'host':<7}{'cell':<5}{'T1':>9}{'T2':>9}{'T3':>9}  {'whole':<6}{'interference':<14}{'I1-I5':<7}{'suite':>6}  candidates (green/defective, red/behavior-ok)")
    for h in HOSTS:
        for c in CELLS:
            if (h, c) not in data:
                continue
            d = data[(h, c)]
            o = d["oracle"]
            if o.get("deferred"):
                print(f"{h:<7}{c:<5}  oracle deferred, not yet scored")
                continue
            cols = []
            for s in ("T1", "T2", "T3"):
                fin = (o.get("features_ok") or {}).get(s)
                alone = (o.get("alone_ok") or {}).get(s)
                cols.append(f"{'ok' if fin else 'NO'}/{'-' if alone is None else ('ok' if alone else 'NO')}")
            inter = o.get("interactions") or {}
            marks = "".join(("." if (inter.get(k) or {}).get("ok") else "X") if isinstance(inter.get(k), dict) else "?" for k in ("I1", "I2", "I3", "I4", "I5"))
            cands = o.get("candidates") or []
            green_bad = sum(1 for x in cands if x.get("retest_ok") and not all((x.get("behavior_ok") or {}).values()))
            red_fine = sum(1 for x in cands if x.get("retest_ok") is False and all((x.get("behavior_ok") or {}).values()))
            print(f"{h:<7}{c:<5}{cols[0]:>9}{cols[1]:>9}{cols[2]:>9}  {'ok' if o.get('whole_tree_ok') else 'NO':<6}{','.join(o.get('interference') or []) or '-':<14}{marks:<7}{fmt(o.get('suite_passed')):>6}  "
                  f"{len(cands)} candidates: {green_bad} green-defective, {red_fine} red-behavior-ok   alone-skipped: {o.get('alone_skipped') or '-'}")
    print("\nWhat really overlapped (the files two tasks' first attempts both changed)")
    for h in HOSTS:
        for c in CELLS:
            if (h, c) in data and c != "s":
                print(f"{h:<7}{c:<5}{data[(h, c)]['write'].get('first_attempt_overlap') or '-'}")


def phases(data: dict) -> None:
    """Where each trial's whole run went, from the ledger and the launcher's clock: launch to the first start (the parent reads the packet, claims and spawns),
    the first round (earliest first start to latest first end), the recovery (that end to the last clean merge: every fix or redo, merge and re-test),
    and the rest (the parent's verification, final report and exit). The control s has no merges: its work is the first start to the last end."""
    print("\nWhere the whole run went, in seconds (launch to first start / first round / recovery after the first round / after the last merge or end)")
    print(f"{'host':<7}{'cell':<5}{'whole':>8}{'to 1st start':>14}{'1st round':>11}{'recovery':>10}{'rest':>8}   recovery as a share of the first round")
    for h in HOSTS:
        for c in CELLS:
            if (h, c) not in data:
                continue
            d = data[(h, c)]
            led = d["ledger"]
            starts = [e["ts"] for e in led if e["kind"] == "start"]
            ends = [e for e in led if e["kind"] in ("end", "fail")]
            merges = [e["ts"] for e in led if e["kind"] == "merged"]
            if not starts or not d["launched"] or not d["whole"]:
                continue
            f0 = min(starts)
            pre = f0 - d["launched"]
            if c == "s":
                work = max(e["ts"] for e in ends) - f0
                print(f"{h:<7}{c:<5}{d['whole']:>8.0f}{pre:>14.0f}{work:>11.0f}{0:>10}{d['whole'] - pre - work:>8.0f}")
                continue
            first_ends = {}
            for e in ends:
                first_ends.setdefault(e["step"], e["ts"])
            e1 = max(first_ends.values())
            last = max(merges) if merges else e1
            first_round = e1 - f0
            recovery = max(0.0, last - e1)
            rest = d["whole"] - pre - first_round - recovery
            print(f"{h:<7}{c:<5}{d['whole']:>8.0f}{pre:>14.0f}{first_round:>11.0f}{recovery:>10.0f}{rest:>8.0f}   {recovery / first_round:.2f}")


def attempt_kinds(data: dict) -> None:
    """The seconds of every attempt, by kind: a first attempt (a fresh worker from the base), a fix attempt (the failed branch with main merged in) and a redo
    (a fresh worker from main's current head). From the ledger's start and end events; the workspace event says which attempt is a fix."""
    print("\nSeconds per attempt, by kind (n, median, shortest to longest), all trials of a host pooled")
    for h in HOSTS:
        kinds = {"first": [], "fix": [], "redo": []}
        for c in ("q0", "qp", "qr"):
            if (h, c) not in data:
                continue
            fix, begun, count = {}, {}, {}
            for e in data[(h, c)]["ledger"]:
                step, kind, det = e["step"], e["kind"], e["detail"]
                if kind == "workspace":
                    fix[(step, det.get("attempt"))] = bool(det.get("fix"))
                elif kind == "start":
                    begun[step] = e["ts"]
                elif kind in ("end", "fail") and step in begun:
                    count[step] = count.get(step, 0) + 1
                    n = count[step]
                    which = "first" if n == 1 else ("fix" if fix.get((step, n)) else "redo")
                    kinds[which].append(e["ts"] - begun.pop(step))
        parts = []
        for which, xs in kinds.items():
            parts.append(f"{which} n={len(xs)}" + (f" median {statistics.median(xs):.0f}, {min(xs):.0f} to {max(xs):.0f}" if xs else ""))
        print(f"  {h:<7}" + "; ".join(parts))


def ratios(data: dict) -> dict:
    print("\nRatios of the whole run (both trials valid and compliant, else n/c)")
    out = {}
    for h in HOSTS:
        parts = []
        for a, b, label in (("qs", "s", "Qs/S"), ("q0", "s", "Q0/S"), ("q0", "qs", "Q0/Qs"), ("qp", "q0", "Qp/Q0"), ("qr", "qp", "Qr/Qp"), ("qp", "s", "Qp/S"), ("qr", "s", "Qr/S")):
            if (h, a) in data and (h, b) in data:
                if ok(data[(h, a)], data[(h, b)]):
                    r = data[(h, a)]["whole"] / data[(h, b)]["whole"]
                    out[(h, label)] = r
                    parts.append(f"{label} {r:.2f}")
                else:
                    parts.append(f"{label} n/c")
        print(f"{h:<7}" + "   ".join(parts))
    print("\nR16 (does fan-out of overlapping real features through a queue pay at this scale?): Q0/S per host, under 0.9 pays, over 1.0 does not, else inconclusive")
    verdicts = {}
    for h in HOSTS:
        r = out.get((h, "Q0/S"))
        verdicts[h] = "n/c" if r is None else ("pays" if r < 0.9 else ("does not pay" if r > 1.0 else "inconclusive"))
    overall = ("pays on all three hosts" if all(v == "pays" for v in verdicts.values()) else
               "does not pay (a host over 1.0)" if any(v == "does not pay" for v in verdicts.values()) else "inconclusive")
    print("  " + ", ".join(f"{h}: {v}" for h, v in verdicts.items()) + f"  =>  {overall}")
    print("R16b (does concurrency itself pay inside the same workflow?): Q0/Qs per host, the same bands")
    for h in HOSTS:
        r = out.get((h, "Q0/Qs"))
        print(f"  {h}: " + ("n/c" if r is None else f"{r:.2f} " + ("pays" if r < 0.9 else ("does not pay" if r > 1.0 else "inconclusive"))))
    return out


def every(parts):
    """A claim about all of them: one false part settles it, an unknown part (a pair that is not valid and compliant) leaves it open."""
    if any(p is False for p in parts):
        return False
    return True if all(p is True for p in parts) else None


def at_least(parts, k):
    """A claim about at least k of them: true once k parts are true, false once k can no longer be reached, otherwise open."""
    got = sum(1 for p in parts if p is True)
    unknown = sum(1 for p in parts if p is None)
    if got >= k:
        return True
    return False if got + unknown < k else None


def hostwise(ratio: dict, label: str, test) -> list:
    return [None if ratio.get((h, label)) is None else bool(test(ratio[(h, label)])) for h in HOSTS]


def shown(ratio: dict, label: str) -> str:
    return "  ".join(f"{h} " + ("n/c" if ratio.get((h, label)) is None else f"{ratio[(h, label)]:.2f}") for h in HOSTS)


def interfered(t: dict, strict: bool = False) -> bool:
    """P79's three clauses. strict=True is the reading that charges a green defect only to a feature that passes on its first branch alone."""
    o = t["oracle"]
    cands = o.get("candidates") or []
    alone = o.get("alone_ok") or {}
    last_green = bool(cands) and bool(cands[-1].get("retest_ok"))
    interaction_bad = (not o.get("interactions_ok")) and last_green

    def defect(c):
        failing = [s for s, v in (c.get("behavior_ok") or {}).items() if not v]
        if strict:
            failing = [s for s in failing if alone.get(s) is True]
        return bool(c.get("retest_ok")) and bool(failing)
    return bool(o.get("interference")) or interaction_bad or any(defect(c) for c in cands)


def predictions(data: dict, ratio: dict) -> None:
    def cells(cell):
        return [data[(h, cell)] for h in HOSTS if (h, cell) in data]

    def verdict(p, label, result, note=""):
        print(f"  {p:<4}{'HELD' if result else ('MISSED' if result is False else 'not scorable')}   {label}" + (f"   [{note}]" if note else ""))
    print("\nPredictions (registered in README Amendment A14; scored as written; a claim about every host is settled by one valid counterexample, and a pair that is not valid and compliant is n/c)")
    q0 = cells("q0")
    verdict("P70", "every q0 trial has an integration failure and a fix attempt",
            (all(t["integration_failures"] >= 1 and (t["write"].get("fix_attempts") or 0) >= 1 for t in q0) if len(q0) == 3 else None),
            "  ".join(f"{t['host']} {t['integration_failures']} failures, {t['write'].get('fix_attempts') or 0} fix" for t in q0))
    six = cells("q0") + cells("qp")
    verdict("P71", "no task ends in mergefail and every q0 and qp trial exits within its timeout",
            (all(t["mergefails"] == 0 and t["score"]["process"]["status"] == "exited" for t in six) if len(six) == 6 else None),
            "  ".join(f"{t['name'][4:]} {t['write'].get('merges')} merged" for t in six))
    verdict("P72", "Q0/S is below 1 on all three hosts", every(hostwise(ratio, "Q0/S", lambda x: x < 1)), shown(ratio, "Q0/S"))
    verdict("P73", "Q0/S is below 0.75 on all three hosts", every(hostwise(ratio, "Q0/S", lambda x: x < 0.75)), shown(ratio, "Q0/S"))
    q = cells("q0") + cells("qp") + cells("qr") + cells("qs")
    pooled = {h: statistics.median([x for t in q if t["host"] == h for x in t["retests"]] or [float("nan")]) for h in HOSTS}
    kit_ok = [(t["write"].get("kit_total_s") or 0) < 90 for t in q]
    verdict("P74", "on every host the median re-test is under 6 s and kit_total_s is under 90 s in every q trial",
            (all(v < 6 for v in pooled.values()) and all(kit_ok) if len(q) == 12 else None),
            "median re-test " + "  ".join(f"{h} {pooled[h]:.1f} s" for h in HOSTS) + "; largest kit_total_s " + fmt(max((t["write"].get("kit_total_s") or 0) for t in q) if q else None))
    qp = cells("qp")
    verdict("P75", "in every qp trial the first attempted integration after the landing fails (a conflict or a red re-test)",
            (all(t["first_after_landing"] in ("conflict", "redtest") for t in qp) if len(qp) == 3 else None),
            "  ".join(f"{t['host']} {t['first_after_landing']}" for t in qp))
    a1 = hostwise(ratio, "Qp/Q0", lambda x: x > 1)
    a2 = hostwise(ratio, "Qp/Q0", lambda x: x < 1.6)
    verdict("P76", "Qp is longer than Q0 on at least two hosts and under 1.6 times Q0 on all three", every([at_least(a1, 2), every(a2)]), shown(ratio, "Qp/Q0"))
    verdict("P77", "Qr is longer than Qp on all three hosts", every(hostwise(ratio, "Qr/Qp", lambda x: x > 1)), shown(ratio, "Qr/Qp"))
    verdict("P78", "Qr is at least 1.3 times Qp on at least two hosts", at_least(hostwise(ratio, "Qr/Qp", lambda x: x >= 1.3), 2), shown(ratio, "Qr/Qp"))
    nine = cells("q0") + cells("qp") + cells("qr")
    if len(nine) == 9 and not any(t["oracle"].get("deferred") for t in nine):
        lit = [t["name"][4:] for t in nine if interfered(t)]
        strict = [t["name"][4:] for t in nine if interfered(t, strict=True)]
        verdict("P79", "interference is observed in at least one of the nine fan-out trials (the three clauses as registered)", bool(lit),
                "as registered: " + (", ".join(lit) or "none") + "; reading that charges a green defect only to a feature that passes alone: " + (", ".join(strict) or "none"))
    else:
        verdict("P79", "interference is observed in at least one of the nine fan-out trials", None)

    def tokens(h):
        x, y = data.get((h, "q0")), data.get((h, "s"))
        if not (x and y and ok(x, y)):
            return None
        if not (x["tokens_complete"] and y["tokens_complete"] and x["tokens"] and y["tokens"]):
            return False   # not scored in P80: the total is incomplete, so this host cannot be one of the two
        return x["tokens"] > y["tokens"]
    t80 = [tokens(h) for h in HOSTS]
    verdict("P80", "Q0's input tokens exceed S's on at least two hosts (hosts with complete totals only, valid and compliant pairs)", at_least(t80, 2),
            "  ".join(f"{h} " + ("n/c" if data.get((h, 'q0')) is None or data.get((h, 's')) is None or not ok(data[(h, 'q0')], data[(h, 's')]) else f"{fmt(data[(h, 'q0')]['tokens'])} vs {fmt(data[(h, 's')]['tokens'])}"
                              + ("" if data[(h, 'q0')]['tokens_complete'] and data[(h, 's')]['tokens_complete'] else " (incomplete)")) for h in HOSTS))
    allt = list(data.values())
    verdict("P81", "at least thirteen of the fifteen trials are valid", (sum(1 for d in allt if d["valid"]) >= 13 if len(allt) == 15 else None),
            f"{sum(1 for d in allt if d['valid'])} of {len(allt)}; invalid: " + (", ".join(d["name"][4:] for d in allt if not d["valid"]) or "none"))
    verdict("P82", "Qs is longer than Q0 on all three hosts (Q0/Qs below 1)", every(hostwise(ratio, "Q0/Qs", lambda x: x < 1)), shown(ratio, "Q0/Qs"))
    verdict("P83", "Qs/S is between 0.9 and 1.5 on every host", every(hostwise(ratio, "Qs/S", lambda x: 0.9 <= x <= 1.5)), shown(ratio, "Qs/S"))
    qs = cells("qs")
    verdict("P84", "no qs trial has an integration failure", (all(t["integration_failures"] == 0 for t in qs) if len(qs) == 3 else None),
            "  ".join(f"{t['host']} {t['integration_failures']}" for t in qs))


def recovery(data: dict) -> None:
    print("\nR17 (observed workflow differences, not isolated costs): Qp minus Q0 and Qr minus Qp, seconds and as a fraction of Q0's slowest first attempt (both trials valid and compliant, else n/c)")
    for h in HOSTS:
        parts = []
        for a, b, label in (("qp", "q0", "Qp-Q0"), ("qr", "qp", "Qr-Qp")):
            if (h, a) in data and (h, b) in data and (h, "q0") in data and ok(data[(h, a)], data[(h, b)], data[(h, "q0")]):
                diff = data[(h, a)]["whole"] - data[(h, b)]["whole"]
                slow = data[(h, "q0")]["write"].get("slowest_first_s")
                parts.append(f"{label} {diff:+.0f} s" + (f" = {diff / slow:+.2f} of Q0's slowest first attempt ({slow:.0f} s)" if slow else ""))
            else:
                parts.append(f"{label} n/c")
        print(f"  {h:<7}" + "   ".join(parts))


def gate(data: dict) -> None:
    print("\nR18 (the re-test as a gate): every attempted clean integration, its green or red re-test against the features' behavior judged offline, all q trials pooled")
    rows = []
    for d in data.values():
        if d["cell"] == "s" or d["oracle"].get("deferred"):
            continue
        alone = d["oracle"].get("alone_ok") or {}
        for c in d["oracle"].get("candidates") or []:
            failing = [s for s, v in (c.get("behavior_ok") or {}).items() if not v]
            rows.append({"trial": d["name"][4:], "step": c.get("step"), "attempt": c.get("attempt"), "red": c.get("retest_ok") is False, "bad": bool(failing),
                         "failing": c.get("failing") or [], "own": [s for s in failing if alone.get(s) is False]})
    bad = [r for r in rows if r["bad"]]
    red = [r for r in rows if r["red"]]
    print(f"  {len(rows)} candidates; {len(red)} red; {len(bad)} with a feature whose behavior fails")
    print(f"  sensitivity (candidates whose behavior fails that were red): {sum(1 for r in bad if r['red'])} of {len(bad)}"
          + f"; precision (red candidates that had a behavior defect): {sum(1 for r in red if r['bad'])} of {len(red)}")
    for r in rows:
        if r["bad"] and not r["red"]:
            print(f"  green defect: {r['trial']} {r['step']} attempt {r['attempt']}: {', '.join(r['failing'])}" + (f"   (the feature also fails on its first branch alone: {', '.join(r['own'])})" if r["own"] else ""))
    for r in red:
        if not r["bad"]:
            print(f"  red the features' behavior does not explain: {r['trial']} {r['step']} attempt {r['attempt']}")
    inter = [(d["name"][4:], [k for k in ("I1", "I2", "I3", "I4", "I5") if not (d["oracle"].get("interactions") or {}).get(k, {}).get("ok")]) for d in data.values() if not d["oracle"].get("deferred")]
    print("  interaction checks failing on final trees: " + ("; ".join(f"{n} {', '.join(f)}" for n, f in inter if f) or "none"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = {(h, c): load(h, c) for h in HOSTS for c in CELLS if have(h, c)}
    table(data)
    phases(data)
    attempt_kinds(data)
    ratio = ratios(data)
    recovery(data)
    gate(data)
    predictions(data, ratio)
    if args.json:
        print(json.dumps({f"{h}-{c}": {"whole": d["whole"], "valid": d["valid"], "compliant": d["compliant"]} for (h, c), d in data.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
