#!/usr/bin/env python3
"""Replay the saved runs for the two questions pre-registered in README.md (this folder), read-only.

    replay.py sendbacks SHIPLOOP_SCRIPTS ROOT [ROOT ...]   # every implement send-back, before any rule is scored
    replay.py score SHIPLOOP_SCRIPTS ROOT [ROOT ...]       # Q1 (rules A/B, C, C') and Q2 (stalls by wording)
    replay.py shipped SHIPLOOP_SCRIPTS ROOT [ROOT ...]     # the follow-up's ship checks 1 and 2
    replay.py closing SHIPLOOP_SCRIPTS ROOT [ROOT ...]     # the closing check: live fires and held-out refusals

Q1 reads each accepted step plan as ``sg1/replay_d6.py`` does (the same run layouts and base rule) and asks three rules:
the shipped ``shiploop_item_scope.proof_order_refusal`` (rules A and B, on each step's Proof); rule C, rule A on each
executed criterion's Confirm-by command; and rule C', rule C on steps whose Proof names no repository path. Each plan C'
refuses is classed from the item's implement outcomes after it and ``labels.jsonl``. Costs come from trace timestamps.
Q2 classes every traced run by the open-item wording its step-plan packets carry, and records whether it stopped at
step-plan. ``score`` writes plans.jsonl, stalls.jsonl and scores.json beside this file.
"""
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[2])
import shiploop_item_scope as scope  # noqa: E402
import shiploop_store as store  # noqa: E402

# The open-item duty's wordings (README Q2), matched on whitespace-collapsed packet text (packets are hard-wrapped):
# fix 1 (8dee00e0), fix 11 (c2da4604), and the wording before fix 11 (`git show c2da4604`, the line it removed).
W1 = "on an executed criterion, or on an expectation for a fact that exists"
W11 = "becomes an expectation whose `from` names it; no other has `from`"
W0 = "An open plan assumption this item consumes becomes an expectation whose `from` names it"
# Refusals of the open-item rule, as score_fx.py counts them.
OPEN_ITEM_REFUSALS = ("as due_item; add an expectation", "as due_item; settle each here", "cite from")
CONFIRM_BY = re.compile(r"confirm by:\s*(.+?)(?:;\s*pass when|;|$)", re.I | re.S)


def runs(roots):
    seen = set()
    for root in roots:
        found = subprocess.run(["find", root, "(", "-name", "node_modules", "-o", "-name", ".git", ")", "-prune",
                                "-o", "-name", "state.md", "-print"], capture_output=True, text=True).stdout.split()
        for path in sorted(found):
            run = Path(path).parent
            if not ((run.name == "run" and run.parent.parent.name == ".shiploop-runs")
                    or (run.name == ".shiploop" and run.parent.name == "work")):
                continue
            if run.resolve() not in seen:
                seen.add(run.resolve())
                yield run


def label_of(run: Path) -> str:
    """The run's folder name relative to its dated parent, as sg1/replay_d6.py prints it."""
    out = run.parent.parent.parent if run.name == "run" else run.parent.parent
    return f"{out.parent.name}/{out.name}"


def read(run: Path):
    try:
        return store.read_record(run / "state.md")
    except Exception:  # noqa: BLE001 - a run the current reader refuses is skipped
        return None


def base_for(run: Path, repo: str, action: str, first_item: bool):
    """sg1/replay_d6.py's rule: the first step's base from the iteration ledger, else the planning close."""
    for ledger in run.glob("iterations/*.json"):
        try:
            plans = json.loads(ledger.read_text()).get("plans") or {}
        except (OSError, ValueError):
            continue
        row = (plans.get(action) or {}).get("S1") or {}
        if row.get("base"):
            return row["base"]
    if first_item:
        found = subprocess.run(["git", "-C", repo, "log", "-1", "--all", "--format=%H", "--grep", "knowledge at prepare"],
                               capture_output=True, text=True).stdout.strip()
        return found or None
    return None


def confirm_by(text) -> str:
    match = CONFIRM_BY.search(str(text or ""))
    return match.group(1).strip() if match else ""


def generic_proof(proof: str) -> bool:
    """A suite command that runs nothing specific to a step (``npm test``, ``pytest``, ``python3 -m unittest -v``): no
    script or test path in any form (absolute, ``../`` or repository-relative) and no inline code.  ``command_paths``
    skips absolute, ``../`` and inline-code words, so its empty answer alone does not make a Proof generic (README,
    results: the reader check)."""
    try:
        words = __import__("shlex").split(proof)
    except ValueError:
        words = proof.split()
    if not words or any(word in ("-e", "-c", "--eval", "-p") for word in words):
        return False
    return not any(("/" in word or re.search(r"\.[A-Za-z][A-Za-z0-9]{0,5}$", word)) and "://" not in word
                   for word in words if not word.startswith("-"))


def confirm_by_hits(plan, exists, no_path_only: bool, generic_only: bool = False):
    """Rule C (or C' with ``no_path_only``): rule A of proof_order_refusal on each executed criterion's Confirm by."""
    item_paths = [str(path) for path in plan.get("paths") or ()]
    if item_paths and all(scope.classify(path) == "test" for path in item_paths):
        return []
    steps = [step for step in plan.get("steps") or () if isinstance(step, dict)]
    ids = [str(step.get("id")) for step in steps]
    declared = {}
    for step in steps:
        for path in step.get("paths") or ():
            declared.setdefault(str(path), []).append(str(step.get("id")))
    criteria = {str(row.get("id")): row for row in plan.get("criteria") or () if isinstance(row, dict)}
    hits = []
    for index, step in enumerate(steps):
        proof = step.get("proof") if isinstance(step.get("proof"), str) else ""
        if no_path_only and scope.command_paths(proof):
            continue
        if generic_only and not generic_proof(proof):
            continue
        earlier = set(ids[:index])
        for cid in step.get("criteria") or ():
            row = criteria.get(str(cid)) or {}
            if row.get("confirm") != "executed":
                continue
            command = confirm_by(row.get("text"))
            for path in scope.command_paths(command):
                if exists(path):
                    continue
                if scope.classify(path) == "test" and not earlier.intersection(declared.get(path, [])):
                    hits.append({"step": ids[index], "criterion": str(cid), "path": path, "proof": proof,
                                 "confirm_by": command[:200]})
                    break
    return hits


def trace_rows(run: Path):
    trace = run / "trace.jsonl"
    if not trace.is_file():
        return []
    rows = []
    for line in trace.read_text(errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get("ts"), (int, float)):
            rows.append(row)
    return rows


def sendbacks(roots) -> None:
    for run in runs(roots):
        state = read(run)
        if not state:
            continue
        accepted = state.get("accepted") or {}
        for row in state.get("history") or ():
            if row.get("stage") == "implement" and row.get("outcome") == "send-back":
                result = accepted.get(row.get("action")) or {}
                print(json.dumps({"run": label_of(run), "path": str(run), "item": row.get("workitem"),
                                  "action": row.get("action"), "summary": str(result.get("summary") or "")[:600]}))


def exact_interval(k: int, n: int):
    """Clopper-Pearson 95% interval for k of n, by bisection on the binomial tail."""
    if n == 0:
        return None

    def tail(p, lower):
        from math import comb
        pmf = [comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
        return sum(pmf[k:]) if lower else sum(pmf[:k + 1])

    def solve(target, lower):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            value = tail(mid, lower)
            if (value < target) == lower:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2, 3)
    low = 0.0 if k == 0 else solve(0.025, True)
    high = 1.0 if k == n else solve(0.025, False)
    return [low, high]


def score(roots) -> None:
    labels = {}
    for line in (HERE / "labels.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            labels[row["action"]] = row["label"]
    plans, stalls, refusal_minutes, sendback_minutes, sendback_rows = [], [], [], [], []
    for run in runs(roots):
        state = read(run)
        if not state:
            continue
        repo, history, accepted = state.get("repo"), state.get("history") or [], state.get("accepted") or {}
        items = [str(w.get("id")) for w in state.get("work_items") or () if isinstance(w, dict)]
        rows = trace_rows(run)
        stage_of = {r.get("action"): r.get("stage") for r in rows if r.get("kind") == "packet"}
        # Costs (README: T_refusal, T_sendback).
        for i, r in enumerate(rows):
            if r.get("kind") == "command" and r.get("verb") == "check" and str(r.get("exit")) != "0" \
                    and stage_of.get(r.get("action")) == "step-plan":
                for later in rows[i + 1:]:
                    if later.get("kind") == "command" and later.get("action") == r.get("action") \
                            and later.get("verb") in ("check", "complete") and str(later.get("exit")) == "0":
                        refusal_minutes.append((later["ts"] - r["ts"]) / 60)
                        break
        for index, row in enumerate(history):
            if row.get("stage") == "implement" and row.get("outcome") == "send-back" \
                    and labels.get(row.get("action")) == "proof-order" and rows:
                start = next((r["ts"] for r in rows if r.get("kind") == "packet" and r.get("action") == row["action"]), None)
                nxt = next((later.get("action") for later in history[index + 1:]
                            if later.get("stage") == "step-plan" and later.get("outcome") == "done"
                            and later.get("workitem") == row.get("workitem")), None)
                end = next((r["ts"] for r in rows if r.get("kind") == "command" and r.get("verb") == "complete"
                            and r.get("action") == nxt and str(r.get("exit")) == "0"), None) if nxt else None
                if start and end:
                    sendback_minutes.append((end - start) / 60)
                    # Descriptive, not registered: an Improve review the re-planned step plan gets before implement.
                    after = [r for r in rows if r["ts"] >= end]
                    review = next((r for r in after if r.get("kind") == "packet"), None)
                    review_minutes = None
                    if review and review.get("stage") == "improve":
                        done_at = next((r["ts"] for r in after if r.get("kind") == "command" and r.get("verb") == "complete"
                                        and r.get("action") == review.get("action") and str(r.get("exit")) == "0"), None)
                        review_minutes = round((done_at - review["ts"]) / 60, 2) if done_at else None
                    sendback_rows.append({"run": label_of(run), "item": row.get("workitem"), "action": row["action"],
                                          "minutes": round((end - start) / 60, 2), "improve_review_after": review_minutes})
        # Q1: every accepted step plan.
        for index, row in enumerate(history):
            plan = accepted.get(row.get("action"))
            if row.get("stage") != "step-plan" or row.get("outcome") != "done" or not isinstance(plan, dict):
                continue
            outcomes, backs = [], []
            for later in history[index + 1:]:
                if later.get("workitem") != row.get("workitem"):
                    continue
                if later.get("stage") == "step-plan":
                    break
                if later.get("stage") == "implement":
                    outcomes.append(later.get("outcome"))
                    if later.get("outcome") == "send-back":
                        backs.append({"action": later.get("action"), "label": labels.get(later.get("action"), "unlabelled"),
                                      "summary": str((accepted.get(later.get("action")) or {}).get("summary") or "")[:240]})
            base = base_for(run, repo, row["action"], bool(items) and row.get("workitem") == items[0]) if repo else None
            judged = bool(base) and subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}^{{commit}}"],
                                                   capture_output=True).returncode == 0
            record = {"run": label_of(run), "item": row.get("workitem"), "action": row.get("action"),
                      "base": (base or "")[:12], "implement_outcomes": outcomes, "send_backs": backs}
            if not judged:
                record.update(unjudged="no base")
            else:
                def exists(path, base=base, repo=repo):
                    return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}:{path}"],
                                          capture_output=True).returncode == 0
                record["shipped"] = scope.proof_order_refusal(plan, exists)[:200]
                record["rule_c"] = confirm_by_hits(plan, exists, no_path_only=False)
                record["rule_c_prime"] = confirm_by_hits(plan, exists, no_path_only=True)
                # Post-hoc (README results): C' as its amendment meant it, generic suite Proofs only.
                record["rule_c_generic"] = confirm_by_hits(plan, exists, no_path_only=True, generic_only=True)
            for key in ("rule_c", "rule_c_prime", "rule_c_generic"):
                if record.get(key):
                    record[key + "_proof_form"] = "generic" if generic_proof(record[key][0]["proof"]) else "direct"
                    if not outcomes:
                        record[key + "_class"] = "unjudged"
                    elif any(b["label"] == "proof-order" for b in backs):
                        record[key + "_class"] = "caught"
                    elif "done" in outcomes:
                        # The registered classes: hollow = passed with a generic Proof (done ran nothing specific to
                        # the criterion); false = passed with a Proof that exercises the step directly.
                        record[key + "_class"] = "hollow" if record[key + "_proof_form"] == "generic" else "false"
                    else:
                        record[key + "_class"] = "other-outcome"
            plans.append(record)
        # Q2: stalls by wording, for traced runs with a step plan.
        packets = [r for r in rows if r.get("kind") == "packet" and r.get("stage") == "step-plan" and r.get("file")]
        if packets:
            texts = []
            for r in packets:
                try:
                    texts.append((run / r["file"]).read_text(errors="ignore"))
                except OSError:
                    pass
            text = " ".join(" ".join(texts).split())
            wording = ("w1" if W1 in text else "w11" if W11 in text else "w0" if W0 in text
                       else "none" if texts else "unread")
            plan_rows = [accepted.get(h.get("action")) or {} for h in history if h.get("stage") == "plan" and h.get("outcome") == "done"]
            due = [a for a in (plan_rows[-1].get("assumptions") or ()) if isinstance(a, dict)
                   and a.get("disposition") == "open" and a.get("due_item")] if plan_rows else []
            refusals = sum(1 for r in rows if any(m in json.dumps(r) for m in OPEN_ITEM_REFUSALS))
            last_stage = next((r.get("stage") for r in reversed(rows) if r.get("kind") == "packet"), None)
            result = {}
            for candidate in (run.parent.parent.parent / "result.json", run.parent.parent / "result.json"):
                if candidate.is_file():
                    try:
                        result = json.loads(candidate.read_text())
                    except ValueError:
                        pass
                    break
            stalls.append({"run": label_of(run), "wording": wording, "open_due": len(due), "open_item_refusals": refusals,
                           "status": state.get("status"), "last_packet_stage": last_stage,
                           "stopped_at_step_plan": state.get("status") in ("paused", "blocked") and last_stage == "step-plan",
                           "outcome": result.get("outcome_class"), "host": result.get("host"), "model": result.get("model"),
                           "case": result.get("case")})
    # Judged plans, plus any unjudged one an implement send-back followed (scores.json counts every plan read).
    (HERE / "plans.jsonl").write_text("".join(json.dumps(p) + "\n" for p in plans
                                              if "unjudged" not in p or p["send_backs"]))
    (HERE / "stalls.jsonl").write_text("".join(json.dumps(s) + "\n" for s in stalls))
    judged = [p for p in plans if "unjudged" not in p]

    def classes(key):
        out = {}
        for p in judged:
            if p.get(key):
                out[p[key + "_class"]] = out.get(p[key + "_class"], 0) + 1
        return out
    caught_beyond = [p for p in judged if p.get("rule_c_prime_class") == "caught" and not p.get("shipped")]
    by_wording = {}
    for s in stalls:
        w = by_wording.setdefault(s["wording"], {"runs": 0, "open_due": 0, "with_refusal": 0, "stopped": 0,
                                                 "stopped_with_open_due": 0})
        w["runs"] += 1
        w["open_due"] += s["open_due"] > 0
        w["with_refusal"] += s["open_item_refusals"] > 0
        w["stopped"] += s["stopped_at_step_plan"]
        w["stopped_with_open_due"] += s["stopped_at_step_plan"] and s["open_due"] > 0
    for w in by_wording.values():
        w["stop_rate_with_open_due_ci95"] = exact_interval(w["stopped_with_open_due"], w["open_due"])
    t_ref = statistics.median(refusal_minutes) if refusal_minutes else None
    t_back = statistics.median(sendback_minutes) if sendback_minutes else None
    c_prime = classes("rule_c_prime")
    decision = None
    if t_ref is not None and t_back is not None:
        caught, hollow = len(caught_beyond), c_prime.get("hollow", 0)
        decision = {"1_caught_beyond_shipped_ge_2": caught >= 2, "2_false_is_0": c_prime.get("false", 0) == 0,
                    "3_net_saving_minutes": round(caught * (t_back - t_ref) - hollow * t_ref, 2)}
        decision["build"] = bool(decision["1_caught_beyond_shipped_ge_2"] and decision["2_false_is_0"]
                                 and decision["3_net_saving_minutes"] > 0)
    # Coverage of every proof-order send-back by the plan it followed (descriptive).
    coverage = []
    for p in plans:
        for back in p["send_backs"]:
            if back["label"] == "proof-order":
                coverage.append({"run": p["run"], "item": p["item"], "send_back": back["action"],
                                 "judged": "unjudged" not in p, "shipped": bool(p.get("shipped")),
                                 "rule_c": bool(p.get("rule_c")), "rule_c_prime": bool(p.get("rule_c_prime"))})
    generic = classes("rule_c_generic")
    generic_caught = [p for p in judged if p.get("rule_c_generic_class") == "caught" and not p.get("shipped")]
    report = {"plans": len(plans), "judged": len(judged), "proof_order_send_backs": coverage,
              "sendback_cost_rows": sendback_rows,
              "shipped_refused": sum(bool(p.get("shipped")) for p in judged),
              "rule_c_classes": classes("rule_c"), "rule_c_prime_classes": c_prime,
              "post_hoc_rule_c_generic": {"classes": generic, "caught_beyond_shipped": len(generic_caught),
                                          "net_saving_minutes": round(len(generic_caught) * ((t_back or 0) - (t_ref or 0))
                                                                      - generic.get("hollow", 0) * (t_ref or 0), 2)},
              "rule_c_prime_caught_beyond_shipped": [f'{p["run"]} {p["item"]}' for p in caught_beyond],
              "T_refusal_minutes": {"median": t_ref, "n": len(refusal_minutes)},
              "T_sendback_minutes": {"median": t_back, "n": len(sendback_minutes)},
              "decision": decision, "stalls_by_wording": by_wording}
    (HERE / "scores.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


def shipped(roots) -> None:
    """The follow-up's ship checks 1 and 2 (README, "Follow-up"): the shipped proof_order_refusal, rule C included,
    against this file's post-hoc ``rule_c_generic`` on every judged plan, and its rule-C refusals on held-out runs (a
    ``state.md`` created after the 2026-11-01 06:14 PST snapshot). Writes shipped-check.json."""
    snapshot = 1793542440  # 2026-11-01 06:14:00 PST
    mismatches, held_out, judged, held_runs = [], [], 0, set()
    for run in runs(roots):
        state = read(run)
        if not state:
            continue
        fresh = (run / "state.md").stat().st_birthtime > snapshot
        if fresh:
            held_runs.add(label_of(run))
        repo, history, accepted = state.get("repo"), state.get("history") or [], state.get("accepted") or {}
        items = [str(w.get("id")) for w in state.get("work_items") or () if isinstance(w, dict)]
        for index, row in enumerate(history):
            plan = accepted.get(row.get("action"))
            if row.get("stage") != "step-plan" or row.get("outcome") != "done" or not isinstance(plan, dict) or not repo:
                continue
            base = base_for(run, repo, row["action"], bool(items) and row.get("workitem") == items[0])
            if not base or subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}^{{commit}}"],
                                          capture_output=True).returncode != 0:
                continue
            judged += 1

            def exists(path, base=base, repo=repo):
                return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}:{path}"],
                                      capture_output=True).returncode == 0
            rules_ab = scope.proof_order_refusal(dict(plan, steps=[dict(s, criteria=[]) for s in plan.get("steps") or ()
                                                                   if isinstance(s, dict)]), exists)
            if rules_ab:
                continue
            new = scope.proof_order_refusal(plan, exists)
            replayed = confirm_by_hits(plan, exists, no_path_only=True, generic_only=True)
            if bool(new) != bool(replayed):
                mismatches.append({"run": label_of(run), "item": row.get("workitem"), "shipped": new[:200],
                                   "replayed": replayed})
            if new and fresh:
                outcomes = [later.get("outcome") for later in history[index + 1:]
                            if later.get("workitem") == row.get("workitem") and later.get("stage") == "implement"]
                held_out.append({"run": label_of(run), "item": row.get("workitem"), "refusal": new,
                                 "implement_outcomes": outcomes})
    report = {"judged": judged, "mismatches": mismatches, "held_out_runs": len(held_runs),
              "held_out_refusals": held_out}
    (HERE / "shipped-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


# Rule C's refusal as proof_order_refusal words it (a refused check's message is the trace row's ``error``), and the
# commit that added rule C.
RULE_C_TEXT = "runs only the tests the item base has"
RULE_C_COMMIT = "9870c6f68bfbd9375340c0e91ffdf4abfd76bd85"


def invocation(run: Path) -> dict:
    """The ``versions`` of the nearest ``invocation.json`` above a run, as step-plan-review-20261101 reads them."""
    for folder in run.parents:
        path = folder / "invocation.json"
        if path.is_file():
            try:
                return json.loads(path.read_text()).get("versions") or {}
            except (OSError, ValueError, AttributeError):
                return {}
    return {}


def rule_c_live(run: Path):
    """Whether the run's ShipLoop had rule C: its checkout's ``local_head`` descends from RULE_C_COMMIT, else its
    ``shiploop_version`` is 1.26.4 or later (the release that shipped it). None when neither is recorded."""
    versions, repo = invocation(run), str(HERE.parents[2])
    head = versions.get("local_head")
    if head and subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{head}^{{commit}}"],
                               capture_output=True).returncode == 0:
        return subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", RULE_C_COMMIT, head],
                              capture_output=True).returncode == 0
    try:
        return tuple(int(part) for part in str(versions.get("shiploop_version")).split(".")[:3]) >= (1, 26, 4)
    except ValueError:
        return None


def closing(roots) -> None:
    """The closing check (README, "Closing check"): on every run whose ``state.md`` was created after the snapshot, the
    rule-C refusals its trace records, and the shipped rule replayed on its accepted step plans after rules A and B pass
    (as ``shipped`` does), split by whether the run's ShipLoop had rule C. Writes closing-check.json."""
    snapshot = 1793542440  # 2026-11-01 06:14:00 PST
    kinds, fires, refusals, without_base = [], [], [], 0
    judged = {"live": 0, "replayed": 0, "unknown": 0}
    for run in runs(roots):
        if (run / "state.md").stat().st_birthtime <= snapshot:
            continue
        state = read(run)
        if not state:
            continue
        kind = {True: "live", False: "replayed", None: "unknown"}[rule_c_live(run)]
        kinds.append(kind)
        for row in trace_rows(run):
            if RULE_C_TEXT in str(row.get("error") or ""):
                fires.append({"run": label_of(run), "kind": kind, "at": row.get("at"), "verb": row.get("verb"),
                              "error": str(row.get("error"))[:600]})
        repo, history, accepted = state.get("repo"), state.get("history") or [], state.get("accepted") or {}
        items = [str(w.get("id")) for w in state.get("work_items") or () if isinstance(w, dict)]
        for index, row in enumerate(history):
            plan = accepted.get(row.get("action"))
            if row.get("stage") != "step-plan" or row.get("outcome") != "done" or not isinstance(plan, dict) or not repo:
                continue
            base = base_for(run, repo, row["action"], bool(items) and row.get("workitem") == items[0])
            if not base or subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}^{{commit}}"],
                                          capture_output=True).returncode != 0:
                without_base += 1
                continue
            judged[kind] += 1

            def exists(path, base=base, repo=repo):
                return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}:{path}"],
                                      capture_output=True).returncode == 0
            if scope.proof_order_refusal(dict(plan, steps=[dict(s, criteria=[]) for s in plan.get("steps") or ()
                                                          if isinstance(s, dict)]), exists):
                continue
            refusal = scope.proof_order_refusal(plan, exists)
            if refusal:
                outcomes = [later.get("outcome") for later in history[index + 1:]
                            if later.get("workitem") == row.get("workitem") and later.get("stage") == "implement"]
                refusals.append({"run": label_of(run), "kind": kind, "item": row.get("workitem"), "refusal": refusal,
                                 "hits": confirm_by_hits(plan, exists, no_path_only=True, generic_only=True),
                                 "implement_outcomes": outcomes})
    report = {"snapshot": snapshot, "runs": len(kinds), "runs_by_kind": {kind: kinds.count(kind) for kind in judged},
              "judged_plans": judged, "plans_without_base": without_base, "live_fires": fires, "refusals": refusals}
    (HERE / "closing-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    {"sendbacks": sendbacks, "score": score, "shipped": shipped, "closing": closing}[sys.argv[1]](sys.argv[3:])
