#!/usr/bin/env python3
"""Read-only evidence mining over ShipLoop E2E run outputs.
Writes a per-run JSON summary to <outdir>/<run>.summary.json and prints
key figures to stdout.
"""
import json, re, sys, os

BASE = os.environ["E2E_RUNS_DIR"]  # directory holding the e2e-run* output directories
OUTDIR = os.environ.get("E4_OUT", os.path.dirname(os.path.abspath(__file__)))

HEAD_RE = re.compile(r'^ShipLoop navigator \| ([a-zA-Z0-9_-]+) \| revision (\d+)', re.M)
FULLPKT_RE = re.compile(r'Full packet:\s*(\S+)')
CALLBACK_ACTION_RE = re.compile(r'Callback for this stage.*?--action=(\S+?)(?:\s|$)')
NEXTCMD_ACTION_RE = re.compile(r'Next command.*?--action=(\S+?)(?:\s|$)')
KEEPALIVE_MARKER_RE = re.compile(r'Keepalive marker: (\S+) run=(\S+) rev=(\d+)')
STATUS_ITEM_RE = re.compile(r'Where:\s+(.*)')
STEP_RE = re.compile(r'\bStep (S\d+) \((\d+) of (\d+)\)')

def load_events(run):
    path = os.path.join(BASE, run, "events.jsonl")
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                events.append({"type": "PARSE_ERROR"})
    return events

def final_text_for(events, i, tcid):
    """Return (text, rawOutput) for the LAST 'completed' update with this toolCallId, scanning forward."""
    text = None
    raw = None
    for j in range(i + 1, min(i + 40, len(events))):
        e2 = events[j]
        if e2.get("toolCallId") == tcid and e2.get("type") == "tool_call_update":
            if e2.get("status") == "completed":
                try:
                    text = e2["content"][0]["content"]["text"]
                except Exception:
                    text = text  # keep prior
                raw = e2.get("rawOutput")
                return text, raw, j
    return text, raw, None

def build_calls(events):
    """Return list of dicts: one per tool_call event, in original order, with resolved output."""
    calls = []
    for i, e in enumerate(events):
        if e.get("type") == "tool_call":
            tcid = e.get("toolCallId")
            text, raw, j = final_text_for(events, i, tcid)
            calls.append({
                "i": i,
                "j": j,
                "toolCallId": tcid,
                "toolName": e.get("toolName"),
                "rawInput": e.get("rawInput", {}),
                "text": text or "",
                "raw": raw,
            })
    return calls

def bytes_of(s):
    return len(s.encode("utf-8", errors="replace")) if s else 0

def analyze_run(run):
    events = load_events(run)
    calls = build_calls(events)

    # ---- locate "exposures" of a packet head (any Bash call whose output contains a HEAD) ----
    exposures = []  # list of dict: call_idx (position in calls list), action, stage, revision, packet_path
    for ci, c in enumerate(calls):
        if c["toolName"] != "run_terminal_command":
            continue
        txt = c["text"]
        m = HEAD_RE.search(txt)
        if not m:
            continue
        stage, revision = m.group(1), int(m.group(2))
        pkt_m = FULLPKT_RE.search(txt)
        packet_path = pkt_m.group(1) if pkt_m else None
        act_m = CALLBACK_ACTION_RE.search(txt) or NEXTCMD_ACTION_RE.search(txt)
        action = act_m.group(1) if act_m else None
        status_m = STATUS_ITEM_RE.search(txt)
        where = status_m.group(1).strip() if status_m else None
        exposures.append({
            "call_idx": ci, "i": c["i"], "stage": stage, "revision": revision,
            "action": action, "packet_path": packet_path, "where": where,
        })

    # ---- locate "complete" invocations per action ----
    completions = []  # dict: call_idx, action, exit_code, command
    for ci, c in enumerate(calls):
        if c["toolName"] != "run_terminal_command":
            continue
        cmd = c["rawInput"].get("command", "")
        if re.search(r'shiploop["\']?\s+complete\b', cmd) or ('shiploop' in cmd and re.search(r'\bcomplete\b.*--run-dir', cmd)):
            am = re.search(r'--action[= ]([A-Za-z0-9_-]+)', cmd)
            action = am.group(1) if am else None
            exit_code = None
            if c["raw"] and isinstance(c["raw"], dict):
                exit_code = c["raw"].get("exit_code")
            completions.append({
                "call_idx": ci, "i": c["i"], "action": action, "exit_code": exit_code,
                "text_head": c["text"][:200],
            })

    # ---- for each exposure, find matching completion (same action, later call_idx) ----
    action_windows = []  # {action, stage, expose_idx, expose_call_idx, complete_call_idx, packet_path}
    for exp in exposures:
        if not exp["action"]:
            continue
        match = None
        for comp in completions:
            if comp["action"] == exp["action"] and comp["call_idx"] > exp["call_idx"] and comp["exit_code"] == 0:
                if match is None or comp["call_idx"] < match["call_idx"]:
                    match = comp
        action_windows.append({
            "action": exp["action"], "stage": exp["stage"], "expose_call_idx": exp["call_idx"],
            "packet_path": exp["packet_path"], "where": exp["where"],
            "complete_call_idx": match["call_idx"] if match else None,
        })

    # dedupe: keep only the LAST exposure per (action) before its completion (recoveries re-expose)
    # but for Q1 we want: was packet read at all between (first exposure) and (completion)? Use union of all exposures for action.
    from collections import defaultdict
    exposures_by_action = defaultdict(list)
    for exp in exposures:
        if exp["action"]:
            exposures_by_action[exp["action"]].append(exp)
    completion_by_action = {}
    for comp in completions:
        if comp["action"] and comp["exit_code"] == 0:
            if comp["action"] not in completion_by_action or comp["call_idx"] < completion_by_action[comp["action"]]["call_idx"]:
                completion_by_action[comp["action"]] = comp

    # ---- Q1: for each action with an exposure + a completion, determine if packet was read in window ----
    q1_results = []
    for action, exps in exposures_by_action.items():
        first_expose_idx = min(e["call_idx"] for e in exps)
        stage = exps[0]["stage"]
        packet_path = next((e["packet_path"] for e in exps if e["packet_path"]), None)
        comp = completion_by_action.get(action)
        if comp is None:
            continue  # never completed (abandoned / run ended) - skip from Q1 counting but note separately
        window_calls = calls[first_expose_idx+1:comp["call_idx"]]
        read_hit = None
        read_kind = None
        for wc in window_calls:
            if packet_path is None:
                break
            if wc["toolName"] == "read_file" and wc["rawInput"].get("target_file") == packet_path:
                limit = wc["rawInput"].get("limit")
                read_hit = wc
                read_kind = "full" if not limit else f"partial(limit={limit})"
                break
            if wc["toolName"] == "run_terminal_command":
                cmd = wc["rawInput"].get("command", "")
                if packet_path in cmd and re.search(r'\b(cat|sed|head|grep|tail|less|more)\b', cmd):
                    read_hit = wc
                    tool_m = re.search(r'\b(cat|sed|head|grep|tail|less|more)\b', cmd)
                    read_kind = f"shell:{tool_m.group(1)}"
                    break
            if wc["toolName"] == "grep" and wc["rawInput"].get("path") == packet_path:
                read_hit = wc
                read_kind = "grep"
                break
        q1_results.append({
            "action": action, "stage": stage, "packet_path": packet_path,
            "read_before_complete": read_hit is not None, "read_kind": read_kind,
            "expose_call_idx": first_expose_idx, "complete_call_idx": comp["call_idx"],
        })

    # ---- Q2: implement-stage windows: bytes of tool output between expose and complete ----
    q2_results = []
    for r in q1_results:
        if r["stage"] != "implement":
            continue
        window_calls = calls[r["expose_call_idx"]+1: r["complete_call_idx"]]
        total_bytes = 0
        packet_bytes = 0
        ref_bytes = 0
        ref_files = []
        for wc in window_calls:
            tb = bytes_of(wc["text"])
            total_bytes += tb
            tf = wc["rawInput"].get("target_file") or wc["rawInput"].get("path") or ""
            if wc["toolName"] == "read_file":
                if tf == r["packet_path"]:
                    packet_bytes += tb
                elif "/references/" in tf or tf.endswith("SKILL.md"):
                    ref_bytes += tb
                    ref_files.append(tf)
        # also find the "where" (work item) for this action, from its exposure
        exps = exposures_by_action[r["action"]]
        where = next((e["where"] for e in exps if e["where"]), None)
        q2_results.append({
            "action": r["action"], "where": where, "total_bytes": total_bytes,
            "packet_bytes": packet_bytes, "ref_bytes": ref_bytes, "ref_files": ref_files,
            "n_calls_in_window": len(window_calls),
        })

    # detect item id from "where" string, e.g. "Work items > W1 "..." (1 of 1) > Build > implement"
    item_re = re.compile(r'Work items > (W\d+)')
    for r in q2_results:
        m = item_re.search(r["where"] or "")
        r["item"] = m.group(1) if m else None

    # repeated reference reads across consecutive implement steps of same item
    from collections import Counter
    item_ref_reuse = defaultdict(Counter)
    prev_item = None
    for r in q2_results:
        for rf in r["ref_files"]:
            item_ref_reuse[r["item"]][rf] += 1

    # ---- Q3: compaction recovery ----
    compactions = []
    for i, e in enumerate(events):
        if e.get("type") in ("auto_compact_started", "auto_compact_completed"):
            compactions.append({"i": i, "type": e.get("type"), "raw": e})
    # pair starts with completions
    q3_results = []
    started_idxs = [c["i"] for c in compactions if c["type"] == "auto_compact_started"]
    completed_idxs = [c["i"] for c in compactions if c["type"] == "auto_compact_completed"]
    for start_i in started_idxs:
        comp_i = next((x for x in completed_idxs if x > start_i), None)
        anchor = comp_i if comp_i else start_i
        # find first tool_call after anchor
        first_call = None
        for e in events[anchor+1:]:
            if e.get("type") == "tool_call":
                first_call = e
                break
        first_cmd = None
        if first_call:
            if first_call.get("toolName") == "run_terminal_command":
                first_cmd = first_call.get("rawInput", {}).get("command", "")[:300]
            else:
                first_cmd = f"[{first_call.get('toolName')}] {json.dumps(first_call.get('rawInput',{}))[:200]}"
        # check for SKILL.md / references read shortly after (next 60 calls)
        skill_reads = []
        count = 0
        for e in events[anchor+1:]:
            if e.get("type") == "tool_call":
                count += 1
                if count > 80:
                    break
                tf = e.get("rawInput", {}).get("target_file", "")
                if tf and ("SKILL.md" in tf or "/references/" in tf):
                    skill_reads.append(tf)
        q3_results.append({
            "start_i": start_i, "completed_i": comp_i,
            "first_call_after": first_cmd,
            "skill_reference_reads_after": skill_reads,
        })

    # ---- Q4: refusals (non-zero exit shiploop commands) ----
    refusals = []
    for ci, c in enumerate(calls):
        if c["toolName"] != "run_terminal_command":
            continue
        cmd = c["rawInput"].get("command", "")
        if "shiploop" not in cmd:
            continue
        exit_code = c["raw"].get("exit_code") if isinstance(c["raw"], dict) else None
        if exit_code not in (0, None):
            verb_m = re.search(r'\bshiploop["\']?\s+([a-z-]+)', cmd) or re.search(r'/shiploop["\']?\s+([a-z-]+)', cmd)
            verb = verb_m.group(1) if verb_m else "?"
            act_m = re.search(r'--action[= ]([A-Za-z0-9_-]+)', cmd)
            action = act_m.group(1) if act_m else None
            first_line = (c["text"].strip().splitlines() or [""])[0][:200]
            refusals.append({"call_idx": ci, "i": c["i"], "verb": verb, "action": action,
                              "exit_code": exit_code, "first_line": first_line})

    # longest consecutive run of refused callbacks for same action
    longest_streak = 0
    longest_streak_action = None
    cur_streak = 0
    cur_action = None
    for r in refusals:
        if r["verb"] == "complete":
            if r["action"] == cur_action:
                cur_streak += 1
            else:
                cur_action = r["action"]
                cur_streak = 1
            if cur_streak > longest_streak:
                longest_streak = cur_streak
                longest_streak_action = cur_action

    # keepalive notices in transcript.md
    transcript_path = os.path.join(BASE, run, "transcript.md")
    keepalive_quotes = []
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        for m in re.finditer(r'.{0,20}ShipLoop keepalive:.{0,120}', content):
            keepalive_quotes.append(m.group(0).strip())
    except FileNotFoundError:
        pass

    # ---- Q5: truncated outputs ----
    result_json_path = os.path.join(BASE, run, "result.json")
    truncated_from_result = []
    try:
        with open(result_json_path) as f:
            rj = json.load(f)
        truncated_from_result = rj.get("cli", {}).get("truncated_outputs", [])
    except Exception:
        pass
    # cross-check: any truncated command reference a packet path or "Full packet"
    truncated_analysis = []
    for t in truncated_from_result:
        s = json.dumps(t)
        is_packet = "packets/" in s or "Full packet" in s
        truncated_analysis.append({"raw": t, "looks_like_packet_related": is_packet})

    summary = {
        "run": run,
        "n_events": len(events),
        "n_calls": len(calls),
        "n_exposures": len(exposures),
        "n_completions": len(completions),
        "q1_total_actions": len(q1_results),
        "q1_read_before": sum(1 for r in q1_results if r["read_before_complete"]),
        "q1_not_read": sum(1 for r in q1_results if not r["read_before_complete"]),
        "q1_results": q1_results,
        "q1_by_stage": {},
        "q2_results": q2_results,
        "q2_item_ref_reuse": {k: dict(v) for k, v in item_ref_reuse.items()},
        "q3_results": q3_results,
        "q4_refusals": refusals,
        "q4_longest_streak": longest_streak,
        "q4_longest_streak_action": longest_streak_action,
        "q4_keepalive_quotes": keepalive_quotes,
        "q5_truncated": truncated_analysis,
    }
    # per-stage Q1 breakdown
    from collections import defaultdict as dd
    stagebrk = dd(lambda: {"total": 0, "read": 0, "not_read": 0})
    for r in q1_results:
        b = stagebrk[r["stage"]]
        b["total"] += 1
        if r["read_before_complete"]:
            b["read"] += 1
        else:
            b["not_read"] += 1
    summary["q1_by_stage"] = dict(stagebrk)

    outpath = os.path.join(OUTDIR, f"{run}.summary.json")
    with open(outpath, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return summary

if __name__ == "__main__":
    runs = sys.argv[1:] or ["e2e-run6", "e2e-run6b", "e2e-run7", "e2e-run7b", "e2e-run8b"]
    for run in runs:
        s = analyze_run(run)
        print(f"\n### {run} ###")
        print("events:", s["n_events"], "calls:", s["n_calls"], "exposures:", s["n_exposures"], "completions:", s["n_completions"])
        print("Q1 total actions w/ completion:", s["q1_total_actions"], "read_before:", s["q1_read_before"], "not_read:", s["q1_not_read"])
        print("Q1 by stage:", s["q1_by_stage"])
        print("Q4 refusals:", len(s["q4_refusals"]), "longest streak:", s["q4_longest_streak"], s["q4_longest_streak_action"])
        print("Q4 keepalive quotes found:", len(s["q4_keepalive_quotes"]))
        print("Q3 compactions:", len(s["q3_results"]))
        print("Q5 truncated:", len(s["q5_truncated"]))
