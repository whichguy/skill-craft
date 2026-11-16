#!/usr/bin/env python3
"""replay_table.py: the tables, the decision rules and the predictions of E18 (the paired fix-versus-redo replay), from the exported evidence.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A15, journal entry E18). Reads evidence/e18-<host>-<f|r><draw>/
(score.json, ledger.jsonl, invocation.json). A trial seeds E17's last failed integration of its host (replay.py) and offers the failed step again to
one fresh worker under one rule: ``f`` fix (the failed branch with main merged in, markers left) or ``r`` redo (main as it is). Four draws a rule and
host; draw i of the two rules is a pair, launched one after the other. Every measure is taken from the ledger after the ``replay_seed`` event, at full
precision (only what is printed is rounded).

  first_attempt_s    the first recovery attempt: its begin (start) to its complete (end)
  recovery_s         the first claim after the seed to the step's merge: the parent's dispatch, the workspace, the attempt or attempts, the merge and the re-test
  claim_to_begin_s   the first claim to the first begin: dispatch, the worker's start and the rule's workspace set-up
  run_s              launch to exit
  retries            integration failures after the seed (a conflict or a red re-test that sent the step round again)

A trial is **compliant** when the treatment happened: at least one fresh agent ran; the first recovery workspace is a fix workspace under ``f`` and
a clean main under ``r``; the seed recorded the rule; the run exited on its own on the requested model and effort. It is **valid** when the oracle
calls the final tree valid, verify is OK, the parent's final report is faithful and the run exited (the scorer's ``valid``). **Flagged** (R20c): a
worker or the parent ran git beyond status, add, commit and a diff with no revision, or named a commit of the state, or a worker named a path of the
study's files outside its trial folder; an unflagged trial means no access was detected, not that none happened.

  python3 replay_table.py            the tables, R20 to R22 and the predictions P85 to P94 where the trials exist
  python3 replay_table.py --json     the per-trial points as JSON
  python3 replay_table.py --selfcheck the bands, the logic of "every host", the boundary cases and P85 to P94 on synthetic trials
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EV = Path(os.environ.get("PPE_EVIDENCE", HERE / "evidence"))
HOSTS = ("claude", "grok", "codex")
ARMS = (("f", "fix"), ("r", "redo"))
DRAWS = (1, 2, 3, 4)
PROFILE = {"claude": ("claude-sonnet-5-5", "high"), "grok": ("grok-4.6", "xhigh"), "codex": ("gpt-6.1-sol", "medium")}
KIT_KINDS = ("workspace", "commit", "merged", "conflict")

# The audit (review R11): a git command is flagged unless its verb is status, add or commit, or a diff with no revision-looking argument; a command that names a commit of the
# state is flagged whatever it is; a path of the study's files named by a worker outside its trial folder is flagged. Complete command text is kept by the scorer.
GIT_CALL = re.compile(r"\bgit\b((?:\s+(?:-[cC]\s+\S+|--?[\w-]+(?:=\S+)?))*)\s+([\w-]+)([^\n;&|]*)")
REVISION = re.compile(r"\bw-T\d-\d\b|\b[0-9a-f]{7,40}\b|\bHEAD[~^@{\d]|\.\.|--all\b|\bmain\b|\borigin\b")
ALLOWED_VERBS = frozenset(("status", "add", "commit"))
STUDY_PATH = re.compile(r"e17|parallel-plan-execution|skill-craft|/evidence/|\.claude/worktrees")


def git_flag(commands: list, shas: list) -> bool:
    for c in commands:
        if any(sha[:7] in c for sha in shas if sha):
            return True
        for m in GIT_CALL.finditer(c):
            verb, rest = m.group(2), m.group(3)
            if verb in ALLOWED_VERBS or (verb == "diff" and not REVISION.search(rest)):
                continue
            return True
    return False


def name(host: str, arm: str, draw: int) -> str:
    return f"e18-{host}-{arm}{draw}"


def fmt(x, nd=1):
    return "n/a" if x is None else (f"{x:,.{nd}f}" if isinstance(x, float) else f"{x:,}")


def load(host: str, arm: str, draw: int) -> dict | None:
    d = EV / name(host, arm, draw)
    if not (d / "score.json").is_file():
        return None
    m = json.loads((d / "score.json").read_text())
    inv = json.loads((d / "invocation.json").read_text())
    ledger = [json.loads(line) for line in (d / "ledger.jsonl").read_text().splitlines() if line.strip()]
    seed = next(e for e in ledger if e["kind"] == "replay_seed")
    step = seed["detail"]["failed_step"]
    after = [e for e in ledger if e["seq"] > seed["seq"]]
    claims = [e for e in after if e["kind"] == "claim" and e["step"] == step]
    starts = [e for e in after if e["kind"] == "start" and e["step"] == step]
    stops = [e for e in after if e["kind"] in ("end", "fail") and e["step"] == step]
    attempts = []
    for i, s in enumerate(starts):
        upto = starts[i + 1]["seq"] if i + 1 < len(starts) else float("inf")
        end = next((x for x in stops if s["seq"] < x["seq"] < upto), None)
        attempts.append(end["ts"] - s["ts"] if end else None)
    merged = next((e for e in after if e["kind"] == "merged" and e["step"] == step), None)
    retests = [e["detail"]["seconds"] for e in after if e["kind"] == "retest" and not e["detail"].get("landing")]
    kit_s = sum((e["detail"].get("seconds") or 0) for e in after if e["kind"] in KIT_KINDS) + sum(retests) \
        + sum((e["detail"].get("seconds") or 0) + (e["detail"].get("reset_s") or 0) for e in after if e["kind"] == "redtest")
    first_ws = next((e["detail"] for e in after if e["kind"] == "workspace" and e["step"] == step), {})
    w = m.get("write") or {}
    o = w.get("oracle") or {}
    tok = m.get("tokens") or {}
    native = m.get("native") or {}
    whole = o.get("whole_tree") or []
    hang = any("(rc None)" in (r.get("output") or "") for r in whole if not r.get("pass"))
    failing = sorted(s for s, ok in (o.get("features_ok") or {}).items() if not ok)
    compliant = bool((native.get("agents") or 0) >= 1 and bool(first_ws.get("fix")) == (arm == "f") and seed["detail"]["rule"] == ("fix" if arm == "f" else "redo")
                     and inv.get("status") == "exited" and (inv.get("model"), inv.get("effort")) == PROFILE[host] and starts)
    diff = d / "attempts" / f"{step}-{seed['detail']['failed_attempt'] + 1}.diff"
    plus = minus = None
    if diff.is_file():
        lines = diff.read_text().splitlines()
        plus = sum(1 for x in lines if x.startswith("+") and not x.startswith("+++"))
        minus = sum(1 for x in lines if x.startswith("-") and not x.startswith("---"))
    launched = inv.get("started")
    retries = sum(1 for e in after if e["kind"] == "retry")
    hang_retest = any(e["kind"] == "retest" and not e["detail"].get("landing") and e["detail"].get("rc") == 124 for e in after)   # a re-test that still did not end after the kit's reruns: cause undetermined (A15)
    retest_reruns = sum(len(e["detail"].get("reruns") or []) for e in after if e["kind"] == "retest" and not e["detail"].get("landing"))
    shas = [(inv.get("replay") or {}).get("failed_commit"), (inv.get("replay") or {}).get("main_commit")]
    worker_git, parent_git, outside = m.get("worker_git") or [], m.get("parent_git") or [], m.get("worker_outside") or []
    flag_git = git_flag(worker_git, shas)
    flag_parent = git_flag(parent_git, shas)
    flag_outside = any(STUDY_PATH.search(p) for p in outside)
    series = [x[1] for x in (inv.get("load_series") or []) if len(x) == 2]
    refused: dict = {}
    for e in after:
        if e["kind"] == "refused":
            refused[e["detail"].get("category")] = refused.get(e["detail"].get("category"), 0) + 1
    return {"name": name(host, arm, draw), "host": host, "arm": arm, "draw": draw, "step": step, "valid": bool(m.get("valid")), "compliant": compliant,
            "git_calls": len(worker_git), "flag_git": flag_git, "flag_parent": flag_parent, "flag_outside": flag_outside, "peek": flag_git or flag_parent or flag_outside,
            "hang_retest": hang_retest, "retest_reruns": retest_reruns, "worker_calls": m.get("worker_calls"), "worker_tests": m.get("worker_tests"),
            "first_attempt_s": attempts[0] if attempts else None, "attempts": attempts,
            "recovery_s": merged["ts"] - claims[0]["ts"] if merged and claims else None,
            "claim_to_begin_s": starts[0]["ts"] - claims[0]["ts"] if starts and claims else None,
            "to_claim_s": claims[0]["ts"] - launched if claims and launched else None,
            "run_s": (m.get("timings") or {}).get("launch_to_exit_s"), "retries": retries, "merged": bool(merged), "merged_first": bool(merged) and retries == 0,
            "redtests": sum(1 for e in after if e["kind"] == "redtest"), "conflicts": sum(1 for e in after if e["kind"] == "conflict"),
            "refused": refused, "retest_s": sum(retests), "kit_s": kit_s,
            "tokens": tok.get("input_all"), "output": tok.get("output_all"), "cost": tok.get("cost_usd"), "tokens_complete": not tok.get("children_without_usage"),
            "load": (inv.get("loadavg") or [None])[0], "load_max": max(series) if series else None, "load_mean": statistics.mean(series) if series else None,
            "failing": failing, "whole_ok": o.get("whole_tree_ok"), "hang": hang, "interactions_ok": o.get("interactions_ok"),
            "suite": o.get("suite_passed"), "plus": plus, "minus": minus, "started": launched, "oracle_deferred": bool(o.get("deferred"))}


def pair_status(f: dict | None, r: dict | None) -> str | None:
    """None when the pair is usable (both trials compliant and both first attempts ended), else why it is not."""
    if not f or not r:
        return "a trial is missing"
    for t in (f, r):
        if not t["compliant"]:
            return f"{t['name']} is not compliant"
        if t["first_attempt_s"] is None:
            return f"{t['name']}'s first attempt did not end"
    return None


def usable(f: dict | None, r: dict | None) -> bool:
    return pair_status(f, r) is None


def ratio(r: dict, f: dict, key: str) -> float | None:
    return r[key] / f[key] if r.get(key) and f.get(key) else None


def band(ratios: list, need: int = 3, factor: float = 1.5) -> str:
    """R20's band for one host, on unrounded ratios: 'redo costs more' (median at least ``factor`` and at least ``need`` pairs above 1), 'fix costs more' (the
    mirror), else 'no difference shown'; fewer than ``need`` usable pairs is 'n/c'."""
    if len(ratios) < need:
        return "n/c"
    med = statistics.median(ratios)
    if med >= factor and sum(1 for x in ratios if x > 1) >= need:
        return "redo costs more"
    if med <= 1 / factor and sum(1 for x in ratios if x < 1) >= need:
        return "fix costs more"
    return "no difference shown"


def overall(bands: dict) -> str:
    """R20's overall reading: 'redo costs more' only if every host with three usable pairs says so (and so none says 'fix costs more'); otherwise the hosts are named."""
    have = {h: b for h, b in bands.items() if b != "n/c"}
    if not have:
        return "inconclusive (no host has three usable pairs)"
    for word in ("redo costs more", "fix costs more"):
        if all(b == word for b in have.values()):
            return word + ("" if len(have) == len(bands) else f" (on {', '.join(have)}; the other hosts are n/c)")
    return "mixed: " + ", ".join(f"{h} {b}" for h, b in have.items())


def host_ratios(data: dict, key: str, skip_flagged: bool = False) -> dict:
    out = {}
    for h in HOSTS:
        out[h] = []
        for i in DRAWS:
            f, r = data.get((h, "f", i)), data.get((h, "r", i))
            if usable(f, r) and not (skip_flagged and (r["peek"] or f["peek"])) and ratio(r, f, key) is not None:
                out[h].append(ratio(r, f, key))
    return out


def table(data: dict) -> None:
    print("E18: the same failed integration offered again to one fresh worker, under the fix rule (f) and the redo rule (r); seconds, tokens over all contexts\n")
    print(f"{'trial':<16}{'order':>6}{'attempt':>9}{'recovery':>10}{'run':>7}{'to begin':>9}{'retry':>6}{'valid':>7}{'compl':>6}{'kit s':>7}{'input tok':>12}{'out tok':>9}{'cost':>7}{'patch +/-':>11}{'git':>6}{'calls/tests':>12}{'load max':>9}  fails")
    for h in HOSTS:
        rows = sorted((t for t in data.values() if t["host"] == h), key=lambda t: t["started"] or 0)
        for n, t in enumerate(rows, 1):
            toks = fmt(t["tokens"]) + ("" if t["tokens_complete"] else "*")
            fails = ",".join(t["failing"]) + (" whole-tree" if t["whole_ok"] is False else "") + (" (a hang)" if t["hang"] else "") + (" I1-5" if t["interactions_ok"] is False else "") \
                + (" RE-TEST DID NOT END: cause undetermined, the draw stays" if t["hang_retest"] else "") + (f" re-test rerun x{t['retest_reruns']}" if t["retest_reruns"] else "") \
                + (f" refused {t['refused']}" if t["refused"] else "")
            marks = ("!" if t["flag_git"] else "") + ("P" if t["flag_parent"] else "") + ("@" if t["flag_outside"] else "")
            print(f"{t['name']:<16}{n:>6}{fmt(t['first_attempt_s']):>9}{fmt(t['recovery_s']):>10}{fmt(t['run_s']):>7}{fmt(t['claim_to_begin_s']):>9}{t['retries']:>6}{str(t['valid']):>7}{str(t['compliant']):>6}"
                  f"{fmt(t['kit_s']):>7}{toks:>12}{fmt(t['output']):>9}{fmt(t['cost'], 2):>7}{(str(t['plus']) + '/' + str(t['minus'])):>11}{(str(t['git_calls']) + marks):>6}"
                  f"{(str(t['worker_calls']) + '/' + str(t['worker_tests'])):>12}{fmt(t['load_max']):>9}  {fails.strip()}")
    print("  (order = the launch order on that host; attempt = the first recovery attempt; recovery = first claim to merge; to begin = first claim to the first begin (dispatch, start and the rule's workspace);")
    print("   patch = the attempt's whole diff against main, the preserved feature included, so under fix it is not the repair worker's edits; * = a child has no usage record;")
    print("   git = the git commands the sub-agents ran, ! = flagged git use or a commit of the state named, P = the parent ran such git, @ = a worker named a path of the study's files outside its folder;")
    print("   calls/tests = the sub-agents' tool calls and how many ran the tests; load max = the one-minute load average's highest sample during the run)")
    print("\nPairs (redo over fix; a pair is usable when both trials are compliant and both attempts ended; ratios unrounded in the rules, printed to two places)")
    print(f"{'host':<8}{'draw':>5}{'attempt f':>11}{'attempt r':>11}{'r/f':>7}{'recov f':>10}{'recov r':>10}{'r/f':>7}{'tokens r/f':>12}  not usable because")
    for h in HOSTS:
        for i in DRAWS:
            f, r = data.get((h, "f", i)), data.get((h, "r", i))
            if not (f or r):
                continue
            why = pair_status(f, r)
            ok = why is None
            tk = r["tokens"] / f["tokens"] if f and r and r["tokens"] and f["tokens"] and r["tokens_complete"] and f["tokens_complete"] else None
            print(f"{h:<8}{i:>5}{fmt(f['first_attempt_s'] if f else None):>11}{fmt(r['first_attempt_s'] if r else None):>11}{(fmt(ratio(r, f, 'first_attempt_s'), 2) if ok else 'n/c'):>7}"
                  f"{fmt(f['recovery_s'] if f else None):>10}{fmt(r['recovery_s'] if r else None):>10}{(fmt(ratio(r, f, 'recovery_s'), 2) if ok else 'n/c'):>7}{fmt(tk, 2):>12}  {why or ''}")


def rules(data: dict) -> dict:
    """R20 (the attempt), R20b (the coordinator's wait), R20c (the sensitivity), R21 (the result), R22 (E17 beside this)."""
    found = {}
    print("\nR20 (completed first recovery attempts, redo over fix, per host, under the compliance conditions; 'redo costs more' = median at least 1.5 and at least 3 pairs above 1; n/c under 3 usable pairs)")
    print("R20b (claim to merge: only the pairs in which both recoveries integrated, so a recovery that never merged is not in it; the launched trials' times are in the table above)")
    for key, label in (("first_attempt_s", "R20 "), ("recovery_s", "R20b")):
        found[key] = {}
        for h, ratios in host_ratios(data, key).items():
            launched = sum(1 for a, _ in ARMS for i in DRAWS if (h, a, i) in data)
            found[key][h] = {"band": band(ratios), "ratios": ratios, "median": statistics.median(ratios) if ratios else None}
            print(f"  {label} {h:<7}{found[key][h]['band']:<22}{len(ratios)} usable pairs of {len(DRAWS)} ({launched} of 8 trials launched)  ratios {[round(x, 2) for x in ratios]}  median {fmt(found[key][h]['median'], 2)}")
            for i in DRAWS:
                why = pair_status(data.get((h, "f", i)), data.get((h, "r", i)))
                if why and key == "first_attempt_s":
                    print(f"       draw {i} left out: {why}")
        found[key]["overall"] = overall({h: found[key][h]["band"] for h in HOSTS})
        print(f"  {label} overall: {found[key]['overall']}")
    found["R20c"] = {}
    for h, ratios in host_ratios(data, "first_attempt_s", skip_flagged=True).items():
        found["R20c"][h] = {"band": band(ratios), "pairs": len(ratios), "agrees": band(ratios) == found["first_attempt_s"][h]["band"]}
        print(f"  R20c {h:<7}{found['R20c'][h]['band']:<22}{len(ratios)} pairs without those where a trial was flagged  ({'agrees with R20' if found['R20c'][h]['agrees'] else 'DISAGREES with R20'})")
    flagged = [t["name"] for t in data.values() if t["peek"]]
    disagree = [h for h in HOSTS if not found["R20c"][h]["agrees"]]
    found["first_attempt_s"]["qualified"] = found["first_attempt_s"]["overall"] if not disagree else \
        f"inconclusive: R20 reads '{found['first_attempt_s']['overall']}' but R20c disagrees on {', '.join(disagree)} (flagged trials: {', '.join(flagged) or 'none'})"
    print(f"  R20 with its sensitivity: {found['first_attempt_s']['qualified']}")
    print("\nR21 (the result: valid trials of four, and what failed)")
    found["valid"] = {}
    for h in HOSTS:
        row = {}
        for arm, _ in ARMS:
            ts = [data[(h, arm, i)] for i in DRAWS if (h, arm, i) in data]
            row[arm] = {"valid": sum(1 for t in ts if t["valid"]), "n": len(ts), "invalid": [(t["name"], t["failing"], t["whole_ok"], t["hang"]) for t in ts if not t["valid"]]}
        found["valid"][h] = row
        less = "no difference of two or more" if abs(row["f"]["valid"] - row["r"]["valid"]) < 2 else ("fix less reliable" if row["f"]["valid"] < row["r"]["valid"] else "redo less reliable")
        print(f"  R21  {h:<7}fix {row['f']['valid']}/{row['f']['n']}  redo {row['r']['valid']}/{row['r']['n']}  ({less})  invalid: {row['f']['invalid'] + row['r']['invalid'] or '-'}")
    print("\nR22 (E17 beside this: the unpaired numbers; magnitudes only, no share of E17's gap is attributed to main moving)")
    for h in HOSTS:
        state = json.loads((HERE / "real-repo" / "replay-states" / h / "state.json").read_text())
        fs = [t["first_attempt_s"] for (hh, a, _), t in data.items() if hh == h and a == "f" and t["first_attempt_s"] is not None]
        rs = [t["first_attempt_s"] for (hh, a, _), t in data.items() if hh == h and a == "r" and t["first_attempt_s"] is not None]
        print(f"  R22  {h:<7}{state['step']} after attempt {state['failed_attempt']}: E17's own repair took {fmt(state['e17_next_attempt_seconds'])} s; replay fix median {fmt(statistics.median(fs)) if fs else 'n/a'} s, "
              f"redo median {fmt(statistics.median(rs)) if rs else 'n/a'} s")
    return found


def every(parts: list) -> str:
    """'every host': one usable counterexample settles it; all hosts usable and holding is held; else not scorable."""
    if any(p is False for p in parts):
        return "MISSED"
    if all(p is True for p in parts):
        return "HELD"
    return "not scorable"


def predictions(data: dict, found: dict) -> dict:
    print("\nPredictions (registered in README A15 before any trial, scored as written; 'not scorable' = a needed pair or host is missing or not usable)")
    n_expected = len(HOSTS) * len(ARMS) * len(DRAWS)
    complete = len(data) == n_expected

    def verdict(host, key, factor):
        ratios = host_ratios(data, key)[host]
        if len(ratios) < 3:
            return None
        return statistics.median(ratios) >= factor and sum(1 for x in ratios if x > 1) >= 3
    p = {}
    p["P85"] = every([verdict(h, "first_attempt_s", 1.5) for h in HOSTS])
    p["P86"] = every([verdict(h, "first_attempt_s", 2.0) for h in HOSTS])
    p["P92"] = every([verdict(h, "recovery_s", 1.5) for h in HOSTS])
    first_try = sum(1 for t in data.values() if t["merged_first"])   # the step merged and nothing was sent round again
    p["P87"] = ("HELD" if first_try >= 22 else "MISSED") if complete else ("MISSED" if len(data) - first_try > n_expected - 22 else "not scorable")
    valid_f = sum(1 for (h, a, i), t in data.items() if a == "f" and t["valid"])
    valid_r = sum(1 for (h, a, i), t in data.items() if a == "r" and t["valid"])
    nf = sum(1 for (h, a, i) in data if a == "f")
    nr = sum(1 for (h, a, i) in data if a == "r")
    p["P88"] = ("HELD" if valid_f >= 11 else "MISSED") if nf == 12 else ("MISSED" if nf - valid_f >= 2 else "not scorable")
    p["P89"] = ("HELD" if valid_r >= 10 else "MISSED") if nr == 12 else ("MISSED" if nr - valid_r >= 3 else "not scorable")
    p["P90"] = ("HELD" if valid_f >= valid_r and valid_f >= 8 else "MISSED") if nf == 12 and nr == 12 else "not scorable"
    tok = []
    for h in HOSTS:
        fs = [t["tokens"] for (hh, a, _), t in data.items() if hh == h and a == "f" and t["compliant"] and t["tokens_complete"] and t["tokens"]]
        rs = [t["tokens"] for (hh, a, _), t in data.items() if hh == h and a == "r" and t["compliant"] and t["tokens_complete"] and t["tokens"]]
        tok.append(None if len(fs) < 3 or len(rs) < 3 else statistics.median(rs) / statistics.median(fs) >= 1.3)
    p["P91"] = every(tok)

    def median_of(host, arm, test):
        xs = [t["first_attempt_s"] for (hh, a, _), t in data.items() if hh == host and a == arm and t["compliant"] and t["first_attempt_s"] is not None]
        return None if len(xs) < 3 else test(statistics.median(xs))
    p["P93"] = every([median_of(h, "f", lambda m: m < 90) for h in HOSTS])
    p["P94"] = every([median_of(h, "r", lambda m: m >= 60) for h in HOSTS])
    stated = {"P85": 75, "P86": 60, "P87": 85, "P88": 70, "P89": 40, "P90": 75, "P91": 65, "P92": 65, "P93": 80, "P94": 85}
    for k in sorted(p):
        print(f"  {k} ({stated[k]}%): {p[k]}")
    scorable = [k for k in p if p[k] != "not scorable"]
    print(f"  {sum(1 for k in scorable if p[k] == 'HELD')} held, {sum(1 for k in scorable if p[k] == 'MISSED')} missed, {len(p) - len(scorable)} not scorable; "
          f"registered expectation of the scorable ones: {sum(stated[k] for k in scorable) / 100:.2f} holds (the ten are correlated, not ten independent checks)")
    print(f"  (valid fix trials {valid_f} of {nf}, valid redo trials {valid_r} of {nr}; trials that merged at their first try {first_try} of {len(data)}; trials that never merged {sum(1 for t in data.values() if not t['merged'])})")
    return p


# ------------------------------------------------------------------ self-check (no model call, no evidence)

def synth(host, arm, draw, attempt, recovery, **kw) -> dict:
    t = {"name": name(host, arm, draw), "host": host, "arm": arm, "draw": draw, "step": "T1", "valid": True, "compliant": True, "first_attempt_s": attempt, "attempts": [attempt],
         "recovery_s": recovery, "claim_to_begin_s": 10.0, "to_claim_s": 20.0, "run_s": recovery + 60.0, "retries": 0, "merged": True, "merged_first": True, "redtests": 0, "conflicts": 0,
         "refused": {}, "retest_s": 1.0, "kit_s": 2.0, "tokens": 1_000_000, "output": 10_000, "cost": None, "tokens_complete": True, "load": 5.0, "load_max": 6.0, "load_mean": 5.5,
         "failing": [], "whole_ok": True, "hang": False, "interactions_ok": True, "suite": 140, "plus": 10, "minus": 2, "started": float(draw), "oracle_deferred": False,
         "git_calls": 0, "flag_git": False, "flag_parent": False, "flag_outside": False, "peek": False, "hang_retest": False, "retest_reruns": 0, "worker_calls": 20, "worker_tests": 3}
    t.update(kw)
    return t


def scenario(factor: dict, over: dict | None = None) -> dict:
    """24 synthetic trials: a fix attempt of 40 + draw seconds, the redo attempt ``factor[host]`` times that; ``over`` maps (host, arm, draw) to changes."""
    data = {}
    for h in HOSTS:
        for i in DRAWS:
            f_s = 40.0 + i
            data[(h, "f", i)] = synth(h, "f", i, f_s, f_s + 30.0)
            data[(h, "r", i)] = synth(h, "r", i, f_s * factor[h], f_s * factor[h] + 30.0, tokens=1_800_000)
    for key, change in (over or {}).items():
        data[key].update(change)
    return data


def selfcheck() -> int:
    import contextlib
    import io
    failures = []

    def expect(label, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + label + (f"  {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(label)

    def run(data):
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            found = rules(data)
            p = predictions(data, found)
        return found, p
    expect("band: three or four pairs well above 1 with a median of 1.5 or more is 'redo costs more'", band([2, 2, 2, 0.9]) == "redo costs more" and band([1.6, 1.6, 1.6]) == "redo costs more")
    expect("band: a median under 1.5 is 'no difference shown'", band([2, 2, 0.9, 0.9]) == "no difference shown" and band([1.4, 1.4, 1.4, 1.4]) == "no difference shown")
    expect("band: the mirror is 'fix costs more'", band([0.5, 0.5, 0.5, 2]) == "fix costs more")
    expect("band: under three usable pairs is n/c", band([3.0, 3.0]) == "n/c" and band([]) == "n/c")
    expect("boundaries are on unrounded ratios: four of 1.496 are not 'redo costs more'; four of 0.666 are 'fix costs more'; a ratio of 1.001 counts as above 1",
           band([1.496] * 4) == "no difference shown" and band([0.666] * 4) == "fix costs more" and band([3, 3, 1.001, 0.9]) == "redo costs more")
    f, r = synth("claude", "f", 1, 100.0, 130.0), synth("claude", "r", 1, 149.6, 179.6)
    expect("ratio is not rounded", ratio(r, f, "first_attempt_s") == 1.496)
    expect("overall: every host with three usable pairs saying so", overall({"claude": "redo costs more", "grok": "n/c", "codex": "redo costs more"}).startswith("redo costs more (on claude, codex"))
    expect("overall: one host without a difference makes it mixed and names the hosts", overall({"claude": "redo costs more", "grok": "no difference shown", "codex": "redo costs more"}).startswith("mixed"))

    found, p = run(scenario({"claude": 3.0, "grok": 3.0, "codex": 3.0}))
    expect("redo three times fix on every host: P85, P86, P87, P88, P89, P90, P91, P92, P93 and P94 all hold",
           all(p[k] == "HELD" for k in ("P85", "P86", "P87", "P88", "P89", "P90", "P91", "P92", "P93", "P94")), json.dumps(p))
    expect("...and R20 and R20b read 'redo costs more' overall, with nothing to qualify it", found["first_attempt_s"]["overall"] == "redo costs more"
           and found["recovery_s"]["overall"] == "redo costs more" and found["first_attempt_s"]["qualified"] == "redo costs more")

    found, p = run(scenario({"claude": 3.0, "grok": 1.0, "codex": 3.0}))
    expect("a host with equal attempts is a usable counterexample: P85 and P86 missed, the others' hosts do not rescue it", p["P85"] == "MISSED" and p["P86"] == "MISSED"
           and found["first_attempt_s"]["grok"]["band"] == "no difference shown" and found["first_attempt_s"]["overall"].startswith("mixed"), json.dumps(p))

    only_two = {("grok", "r", i): {"compliant": False} for i in (3, 4)}
    found, p = run(scenario({"claude": 3.0, "grok": 3.0, "codex": 3.0}, only_two))
    expect("a host with two usable pairs is n/c and the claim about every host is not scorable while the others hold", p["P85"] == "not scorable" and found["first_attempt_s"]["grok"]["band"] == "n/c", json.dumps(p))

    found, p = run(scenario({"claude": 3.0, "grok": 3.0, "codex": 1.0}, only_two))
    expect("...but a usable counterexample on another host settles it even though one host is n/c", p["P85"] == "MISSED", json.dumps(p))

    def first_try(**kw):
        return {k: {"retries": 1, "merged_first": False} for k in kw["keys"]}
    two = first_try(keys=[("claude", "f", 1), ("grok", "r", 2)])
    three = first_try(keys=[("claude", "f", 1), ("grok", "r", 2), ("codex", "r", 3)])
    expect("P87: two trials sent round again hold, three miss", run(scenario({h: 3.0 for h in HOSTS}, two))[1]["P87"] == "HELD" and run(scenario({h: 3.0 for h in HOSTS}, three))[1]["P87"] == "MISSED")
    none_merged = {k: {"merged": False, "merged_first": False, "retries": 0, "first_attempt_s": None, "recovery_s": None, "compliant": False} for k in scenario({h: 3.0 for h in HOSTS})}
    expect("P87: twenty-four trials that never began or merged do not hold it (zero retries is not first-try integration)", run(scenario({h: 3.0 for h in HOSTS}, none_merged))[1]["P87"] == "MISSED")

    inv_f1 = {("claude", "f", 1): {"valid": False}}
    inv_f2 = {("claude", "f", 1): {"valid": False}, ("grok", "f", 2): {"valid": False}}
    expect("P88: one invalid fix trial holds, two miss", run(scenario({h: 3.0 for h in HOSTS}, inv_f1))[1]["P88"] == "HELD" and run(scenario({h: 3.0 for h in HOSTS}, inv_f2))[1]["P88"] == "MISSED")
    inv_r2 = {("claude", "r", 1): {"valid": False}, ("grok", "r", 2): {"valid": False}}
    inv_r3 = {**inv_r2, ("codex", "r", 3): {"valid": False}}
    expect("P89: two invalid redo trials hold, three miss", run(scenario({h: 3.0 for h in HOSTS}, inv_r2))[1]["P89"] == "HELD" and run(scenario({h: 3.0 for h in HOSTS}, inv_r3))[1]["P89"] == "MISSED")
    expect("P90: fewer valid fix trials than redo trials misses; equal at zero valid in both arms also misses (it needs at least eight valid fix trials)",
           run(scenario({h: 3.0 for h in HOSTS}, inv_f1))[1]["P90"] == "MISSED" and run(scenario({h: 3.0 for h in HOSTS}, inv_r2))[1]["P90"] == "HELD"
           and run(scenario({h: 3.0 for h in HOSTS}, {k: {"valid": False} for k in scenario({h: 3.0 for h in HOSTS})}))[1]["P90"] == "MISSED")

    incomplete = {("claude", "r", i): {"tokens_complete": False} for i in DRAWS}
    expect("P91: a host whose redo totals are incomplete is not scorable, and a low ratio misses",
           run(scenario({h: 3.0 for h in HOSTS}, incomplete))[1]["P91"] == "not scorable"
           and run(scenario({h: 3.0 for h in HOSTS}, {("codex", "r", i): {"tokens": 1_100_000} for i in DRAWS}))[1]["P91"] == "MISSED")

    slow_fix = {("grok", "f", i): {"first_attempt_s": 100.0} for i in DRAWS}
    quick_redo = {("codex", "r", i): {"first_attempt_s": 50.0} for i in DRAWS}
    expect("P93: a host whose median fix attempt is 90 s or more misses; P94: a host whose median redo attempt is under 60 s misses",
           run(scenario({h: 3.0 for h in HOSTS}, slow_fix))[1]["P93"] == "MISSED" and run(scenario({h: 3.0 for h in HOSTS}, quick_redo))[1]["P94"] == "MISSED")

    peeks = {("claude", "r", i): {"peek": True, "flag_git": True} for i in (1, 2)}
    found, p = run(scenario({h: 3.0 for h in HOSTS}, peeks))
    expect("R20c: leaving out the pairs with a flagged trial leaves two pairs, so that host is n/c, disagrees with R20, and R20's reading is qualified as inconclusive",
           found["R20c"]["claude"]["band"] == "n/c" and found["R20c"]["claude"]["agrees"] is False and found["R20c"]["grok"]["agrees"] is True
           and found["first_attempt_s"]["qualified"].startswith("inconclusive") and found["first_attempt_s"]["overall"] == "redo costs more", json.dumps(found["R20c"]))

    expect("the audit flags revision-qualified and option-prefixed git, the state's commits, and reads of the history; it lets status, add, commit and a plain diff pass",
           git_flag(["git diff bcb16dc05254f8e8ed8820804e18ed2eeabcaa71 HEAD -- src/store.js"], []) and git_flag(["git --no-pager show bcb16dc05254f8e8ed8820804e18ed2eeabcaa71:src/store.js"], [])
           and git_flag(["git -C ws log --oneline"], []) and git_flag(["echo x && git diff main"], []) and git_flag(["cat a", "ls x " + "a" * 300 + " && git log"], [])
           and git_flag(["sed -n 1,5p b"], ["01545c50ffff"]) is False and git_flag(["sed -n 1,5p b 01545c5"], ["01545c50ffff"])
           and not git_flag(["git status", "git add -A", "git diff", "git diff --name-only --diff-filter=U", "git commit -m x"], []))
    expect("a path of the study's files outside a trial's folder is flagged", bool(STUDY_PATH.search("/Users/dadleet/e17-runs-20261115/x")) and bool(STUDY_PATH.search("/Users/dadleet/src/skill-craft/docs"))
           and not STUDY_PATH.search("/Users/dadleet/.npm/_logs/x.log"))

    print("SELFCHECK " + ("OK" if not failures else "FAILED: " + "; ".join(failures)))
    return 0 if not failures else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selfcheck", action="store_true", help="the bands, the logic of 'every host', the boundary cases and P85 to P94 on synthetic trials (no model call, no evidence)")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    data = {}
    for h in HOSTS:
        for arm, _ in ARMS:
            for i in DRAWS:
                t = load(h, arm, i)
                if t:
                    data[(h, arm, i)] = t
    if not data:
        print(f"no e18 trials in {EV}")
        return 1
    if args.json:
        print(json.dumps(list(data.values()), indent=1, default=str))
        return 0
    table(data)
    found = rules(data)
    predictions(data, found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
