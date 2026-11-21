#!/usr/bin/env python3
"""One summary of Ratchet pilot runs, read from their records alone. No model is called and nothing is graded here.

    python3 analyze.py OUT.json RUN [RUN ...]

For every run folder it reads run.json, the sessions' event streams (the token counts each host reports when a
session ends), the stage reports under work/ratchet/, the work repository's stage commits, and hidden.json and
strength.json where grade.py has written them. It writes OUT.json and prints three tables:

  whole loops     minutes and tokens by stage, each cycle's gate, what each closing look added and how many of its
                  additions its own report marks "product keeps to it: no", product lines changed by each later build,
                  held-out checks at the first build and at the end
  repair starts   the gate and the held-out checks at the start and at the end, fix and referee sessions, disputes
  test strength   clauses and use cases, how many fail on the correct reference, defects caught

A run still in flight is summarised as far as it has got and marked `finished: false`.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def git(work, *args):
    done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def usage(folder):
    """The token counts a session's host reported when it ended: {input, cached, output, reasoning}, or {}."""
    events = folder / "events.jsonl"
    found = {}
    if not events.exists():
        return found
    for line in events.read_text(errors="replace").splitlines():
        if '"usage"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("usage"), dict):
            use = event["usage"]
            found = {"input": use.get("input_tokens") or 0, "cached": use.get("cache_read_input_tokens") or 0,
                     "output": use.get("output_tokens") or 0, "reasoning": use.get("reasoning_tokens") or 0}
    return found


def lines_changed(work, older, newer):
    """Product lines added and removed between two commits, the apparatus's own folders left out."""
    stat = git(work, "diff", "--numstat", older, newer, "--", ".", ":!ratchet", ":!acceptance")
    added = removed = files = 0
    for row in stat.splitlines():
        parts = row.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            added, removed, files = added + int(parts[0]), removed + int(parts[1]), files + 1
    return {"files": files, "added": added, "removed": removed}


def summarise(run):
    run = Path(run).resolve()
    record = json.loads((run / "run.json").read_text())
    work = run / "work"
    row = {"run": run.name, "case": record["case"], "model": record.get("model"), "effort": record.get("effort"),
           "finished": "finished" in record, "stop": record.get("stop"), "final_pass": record.get("final_pass"),
           "minutes": round((record.get("seconds") or 0) / 60, 1) or None, "sessions": len(record["sessions"]),
           "clauses": record.get("clauses"), "use_cases": record.get("use_cases"),
           "kind": ("repair start" if record.get("frozen_from") else "test strength" if record.get("build_from") else "whole loop"),
           "tamper": len(record.get("tamper") or []), "reverted": record.get("reverted") or [],
           "spec_violations": record.get("spec_violations") or [],
           "held_out_marks": sorted({mark for s in record["sessions"] for mark in s.get("held_out_marks") or []})}
    by_role, tokens = {}, {"input": 0, "cached": 0, "output": 0, "reasoning": 0}
    for session in record["sessions"]:
        by_role[session["role"]] = by_role.get(session["role"], 0) + session["seconds"]
        use = usage(run / "sessions" / f"{session['number']:02d}-{session['label']}")
        for key in tokens:
            tokens[key] += use.get(key, 0)
    row["minutes_by_stage"] = {role: round(seconds / 60, 1) for role, seconds in by_role.items()}
    if record.get("seconds"):
        row["minutes_by_stage"]["gates and script"] = round((record["seconds"] - sum(by_role.values())) / 60, 1)
    row["tokens"] = tokens
    snaps = {shot["label"]: shot for shot in record["snapshots"]}
    first_build = next((label for label in snaps if label.startswith("build-")), None)
    row["minutes_to_first_build"] = round(snaps[first_build]["at"] / 60, 1) if first_build else None
    gates = {gate["label"]: gate for gate in record["gates"]}
    cycles = []
    for cycle in record.get("cycles") or []:
        n = cycle["cycle"]
        gate = gates.get(f"cycle-{n}-first")
        entry = {"cycle": n, "plan_added": cycle.get("plan_added") or [],
                 "first_gate": None if not gate else f"{len(gate['passing'])} of {gate['clauses']}",
                 "first_gate_failing": cycle.get("first_gate_failing"),
                 "fix_sessions": len(cycle.get("fix_loops") or []), "disputes": len(cycle.get("disputes") or []),
                 "referee_refused": len(cycle.get("referee_refused") or []),
                 "delta_added": list(cycle.get("delta_clauses") or {}) if "delta_clauses" in cycle else None}
        report = work / "ratchet" / f"delta-{n}.md"
        if report.is_file():
            text = report.read_text()
            entry["delta_keeps_no"] = len(re.findall(r"keeps to it:\s*\**\s*no\b", text, re.IGNORECASE))
            entry["delta_keeps_yes"] = len(re.findall(r"keeps to it:\s*\**\s*yes\b", text, re.IGNORECASE))
        if n > 1 and f"green-{n - 1}" in snaps and f"build-{n}" in snaps:
            entry["build_changed"] = lines_changed(work, snaps[f"green-{n - 1}"]["commit"], snaps[f"build-{n}"]["commit"])
        cycles.append(entry)
    row["cycles"] = cycles
    start = snaps.get("frozen suite of an earlier run")
    if start and "final" in snaps:
        row["product_changed"] = lines_changed(work, start["commit"], snaps["final"]["commit"])
        tests = git(work, "diff", "--shortstat", start["commit"], snaps["final"]["commit"], "--", "acceptance", "ratchet/acceptance.json")
        row["frozen_tests_changed"] = tests or "unchanged"
        row["referee_sessions"] = sum(1 for s in record["sessions"] if s["role"] == "referee")
        row["fix_sessions"] = sum(1 for s in record["sessions"] if s["role"] == "fix")
        first, last = record["gates"][0], record["gates"][-1]
        row["gate_start"], row["gate_end"] = f"{len(first['passing'])} of {first['clauses']}", f"{len(last['passing'])} of {last['clauses']}"
        row["gate_end_failing"] = last["failing"]
    hidden_file = run / "hidden.json"
    if hidden_file.exists():
        hidden = json.loads(hidden_file.read_text())

        def passed(label):
            mark = hidden.get(label)
            if not mark:
                return None
            return {"passed": len(mark.get("effective_passed") or mark.get("passed") or []), "failed": sorted(mark.get("failed") or {}),
                    "observed": bool(mark.get("observed")), "rerun": "rerun" in mark}
        row["hidden"] = {label: passed(label) for label in hidden}
        row["hidden_first_build"] = passed(first_build) if first_build else None
        row["hidden_start"] = passed("frozen suite of an earlier run")
        row["hidden_final"] = passed("final")
    strength_file = run / "strength.json"
    if strength_file.exists():
        strength = json.loads(strength_file.read_text())
        row["strength"] = {key: strength.get(key) for key in ("clauses", "use_cases", "caught", "pool", "not_judged", "graded_with")}
        row["strength"]["clauses_failing_on_reference"] = len(strength.get("clauses_failing_on_reference") or [])
        row["strength"]["use_cases_failing_on_reference"] = len(strength.get("use_cases_failing_on_reference") or [])
        wrong = set(strength.get("fails_on_reference") or [])
        for name, control in (strength.get("controls") or {}).items():
            extra = sorted(set(control.get("failing") or []) - wrong) if "error" not in control else None
            row["strength"][f"control_{name}_fails_beyond_reference"] = None if extra is None else len(extra)
        row["strength"]["missed"] = sorted(name for name, d in (strength.get("defects") or {}).items() if d.get("caught") is False)
    return row


def table(rows):
    whole = [row for row in rows if row["kind"] == "whole loop"]
    if whole:
        print("WHOLE LOOPS")
        for row in whole:
            hidden = row.get("hidden_first_build"), row.get("hidden_final")
            print(f"- {row['run']} ({row['model']} {row['effort']}): {'finished' if row['finished'] else 'in flight'}, stop {row['stop']}, "
                  f"{row['minutes']} min, {row['sessions']} sessions, first build at {row['minutes_to_first_build']} min; held-out first build "
                  f"{hidden[0]['passed'] if hidden[0] else '?'}, final {hidden[1]['passed'] if hidden[1] else '?'}; tokens out "
                  f"{row['tokens']['output']:,}, in {row['tokens']['input']:,} ({row['tokens']['cached']:,} cached)")
            print(f"    minutes by stage: {row['minutes_by_stage']}")
            for cycle in row["cycles"]:
                changed = cycle.get("build_changed")
                print(f"    cycle {cycle['cycle']}: gate {cycle['first_gate']}, failing {cycle['first_gate_failing']}, fix sessions {cycle['fix_sessions']}, "
                      f"plan added {len(cycle['plan_added'])}, closing look added {None if cycle['delta_added'] is None else len(cycle['delta_added'])} "
                      f"(product keeps: no {cycle.get('delta_keeps_no')}, yes {cycle.get('delta_keeps_yes')})"
                      + (f", build changed +{changed['added']} -{changed['removed']} in {changed['files']} files" if changed else ""))
    repairs = [row for row in rows if row["kind"] == "repair start"]
    if repairs:
        print("REPAIR STARTS")
        for row in repairs:
            start, end = row.get("hidden_start"), row.get("hidden_final")
            print(f"- {row['run']}: stop {row['stop']}, {row['minutes']} min; gate {row.get('gate_start')} -> {row.get('gate_end')}; held-out "
                  f"{start['passed'] if start else '?'} -> {end['passed'] if end else '?'}; fix {row.get('fix_sessions')}, referee {row.get('referee_sessions')}, "
                  f"disputes {sum(c['disputes'] for c in row['cycles'])}; product +{(row.get('product_changed') or {}).get('added')} lines; frozen tests "
                  f"{row.get('frozen_tests_changed')}; still failing {row.get('gate_end_failing')}")
    strong = [row for row in rows if row["kind"] == "test strength" and row.get("strength")]
    if strong:
        print("TEST STRENGTH")
        for row in strong:
            s = row["strength"]
            print(f"- {row['run']}: {s['clauses']} clauses, {s['use_cases']} use cases; failing on the reference {s['clauses_failing_on_reference']} "
                  f"clauses, {s['use_cases_failing_on_reference']} use cases; caught {s['caught']} of {s['pool']}; missed {s['missed']}; "
                  f"second correct delivery fails {s.get('control_alternative_fails_beyond_reference')} more; {row['minutes']} min; "
                  f"tokens out {row['tokens']['output']:,}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    rows = []
    for run in argv[1:]:
        if (Path(run) / "run.json").exists():
            rows.append(summarise(run))
    Path(argv[0]).write_text(json.dumps(rows, indent=1) + "\n")
    table(rows)


if __name__ == "__main__":
    main()
