#!/usr/bin/env python3
"""Read a round of whole deliveries: what the harness judged, what the run cost, and what happened at the release stages.

Usage: ``read_round.py ROOT [NAME ...] [--json FILE] [--table FILE]``.  ROOT holds one output folder per delivery (``launch_wave.sh``);
with no NAME every folder that holds a ``result.json`` is read.  ``read_wave.py`` reads what a delivery recorded and
showed about its ``defaults``; this script reads the rest of what a round's entry reports, from the delivery's own
files and nothing else:

- the harness's five verdicts, its outcome and each case check (a failed check with the end of its output);
- the build (versions, plugin fingerprint, the commit built, the harness's evaluator and oracle digests, the host's
  build);
- start, end and minutes; turns, model calls, output tokens and the cost the host reported;
- accepted revisions, the stage reviews (how many, their passes, how many changed something), and every refused
  ShipLoop command of the run's trace by stage, with those that name ``defaults`` listed apart;
- the work items with their regression commands, the consumer checks release-plan recorded, the release stages in
  order, and each release-verify record: where it ran and each command with whether ShipLoop added it, its status,
  exit code, test count and seconds;
- the list of defaults: the rows the accepted spec result holds (and how many name a roll-back), whether the next
  stage's packet printed its block, whether the report has its section right after the request, and the list as the
  last packet that carries it printed it (how many rows, how many marked as changed);
- the returned checkout (committed, its head, anything uncommitted) and what the harness found left behind;
- the host's last message to the user, whole.

It writes nothing into a delivery's folder.  Home paths are printed as ``~``.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

RECORD = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
DONE_ROW = re.compile(r"^\d+\. R-\d+ ")
ROLL_BACK = re.compile(r"roll(ing|ed)?[ -]?back|1\.4\.0|downgrad", re.IGNORECASE)
VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
RELEASE = ("release-plan", "release", "release-verify")
HOME = os.path.expanduser("~")


def tilde(text: object) -> str:
    return str(text).replace(HOME, "~")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def record(path: Path) -> dict:
    """The JSON a ShipLoop record file carries in its fenced block; empty when there is none."""
    try:
        found = RECORD.search(path.read_text(encoding="utf-8", errors="replace"))
        return json.loads(found.group(1)) if found else {}
    except (OSError, json.JSONDecodeError):
        return {}


def clock(stamp: float | None) -> str | None:
    if not stamp:
        return None
    return datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).strftime("%H:%M:%SZ")


def refusals(run: Path) -> list[dict]:
    """Every ShipLoop command of the trace that exited non-zero with an error text: its stage and the text."""
    rows = []
    try:
        lines = (run / "trace.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "command" and row.get("exit") and row.get("error"):
            stage = row.get("stage")
            rows.append({"stage": stage[0] if isinstance(stage, list) and stage else stage,
                         "text": " ".join(str(row["error"]).split())})
    return rows


def done_packet(run: Path) -> dict:
    """The list as the last packet that carries it printed it: the packet's file and the numbered rows under its head
    line.  A run whose list is empty or absent prints no such line (the report carries "none" or "not recorded")."""
    found = {"packets_with_the_list": 0, "file": None, "rows": 0, "marked_changed": 0}
    holders = [path for path in (run / "packets").glob("*.md")
               if "\nDecided for you: " in "\n" + path.read_text(encoding="utf-8", errors="replace")]
    found["packets_with_the_list"] = len(holders)
    if holders:
        last = max(holders, key=lambda path: path.stat().st_mtime)
        lines = last.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(index for index, line in enumerate(lines) if line.startswith("Decided for you: "))
        rows = []
        for line in lines[start + 1:]:
            if not DONE_ROW.match(line):
                break
            rows.append(line)
        found.update(file=last.name, rows=len(rows),
                     marked_changed=sum(1 for line in rows if "(changed after the spec stage)" in line))
    return found


def last_message(out: Path) -> str | None:
    """The host's last message to the user, whole: the last ``text`` event of a Codex or Grok run, or the ``result``
    event of a Claude Code run, from the harness's copy of the host's events."""
    text = None
    try:
        lines = (out / "events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text" and isinstance(event.get("data"), str) and event["data"].strip():
            text = event["data"]
        elif event.get("type") == "result" and isinstance(event.get("result"), str) and event["result"].strip():
            text = event["result"]
    return tilde(text) if text else None


def the_list(run: Path, state: dict) -> dict:
    """The accepted spec result's ``defaults`` (how many rows, and each row's requirement and question), whether the
    packet of the next stage printed its block, and whether the report carries its section right after the request."""
    accepted = state.get("accepted") or {}
    specs = [row["action"] for row in state.get("history") or [] if row.get("stage") == "spec" and row.get("outcome") == "done"]
    result = accepted.get(specs[-1]) if specs else None
    entries = result.get("defaults") if isinstance(result, dict) else None
    shown = {"recorded": isinstance(entries, list), "rows": len(entries) if isinstance(entries, list) else None,
             "questions": [f"{entry.get('requirement')} {entry.get('question')}" for entry in entries or []
                           if isinstance(entry, dict)],
             "entries": [entry for entry in entries or [] if isinstance(entry, dict)],
             "roll_back_rows": sum(1 for entry in entries or [] if isinstance(entry, dict)
                                   and ROLL_BACK.search(" ".join(str(value) for value in entry.values())))}
    next_packets = [run / "packets" / (row["action"] + ".md") for row in state.get("history") or []
                    if row.get("stage") == "test-strategy"]
    shown["next_stage_packets_with_the_block"] = sum(
        1 for path in next_packets if path.is_file()
        and "\nDefaults the spec recorded:" in "\n" + path.read_text(encoding="utf-8", errors="replace"))
    report = run / "report.html"
    if report.is_file():
        text = report.read_text(encoding="utf-8", errors="replace")
        request, heading, after = "<h2>Original request</h2>", "<h2>Decided for you</h2>", "<h2>Accepted transitions</h2>"
        shown["report_section"] = heading in text
        shown["report_section_right_after_the_request"] = (
            request in text and heading in text and after in text
            and text.index(request) < text.index(heading) < text.index(after))
    else:
        shown["report_section"] = None
    return shown


def release(run: Path, state: dict) -> dict:
    accepted = state.get("accepted") or {}
    history = state.get("history") or []
    items = []
    for item in state.get("work_items") or []:
        plans = [row["action"] for row in history if row.get("stage") == "step-plan"
                 and row.get("workitem") == item.get("id") and row.get("outcome") == "done"]
        commands = [row.get("command") for row in (accepted.get(plans[-1]) or {}).get("test_commands") or []
                    if row.get("suite") == "regression" or row.get("regression")] if plans else []
        steps = (accepted.get(plans[-1]) or {}).get("steps") if plans else None
        items.append({"id": item.get("id"), "title": str(item.get("title") or "")[:80],
                      "regression_commands": commands, "steps": len(steps) if isinstance(steps, list) else None})
    checks = [[tilde(row.get("command")) for row in (accepted.get(entry.get("action")) or {}).get("consumer_checks") or []]
              for entry in history if entry.get("stage") == "release-plan" and entry.get("outcome") == "done"]
    order = [f"{row.get('stage')}:{row.get('outcome')}" for row in history
             if row.get("workitem") is None and row.get("stage") in RELEASE]
    verify = []
    for row in history:
        if row.get("stage") != "release-verify":
            continue
        for path in sorted((run / "tests").glob(f"{row['action']}-verify*.md")):
            rec = record(path)
            observed = rec.get("observed") or {}
            verify.append({"record": path.name, "action_ended": row.get("outcome"), "where": observed.get("where"),
                           "head": str(observed.get("head") or "")[:12], "passed": rec.get("passed"),
                           "disposition": rec.get("disposition"),
                           "runs": [{"added": bool(run_row.get("from_step_plan")), "suite": run_row.get("suite"),
                                     "command": tilde(run_row.get("command")), "status": run_row.get("status"),
                                     "exit": run_row.get("exit"), "ran": (run_row.get("counts") or {}).get("ran"),
                                     "seconds": run_row.get("seconds")} for run_row in rec.get("runs") or []]})
    return {"work_items": items, "consumer_checks": checks, "release_stages": order, "release_verify": verify}


def read(out: Path) -> dict:
    result, metrics = load(out / "result.json"), load(out / "metrics.json")
    span = result.get("span") or {}
    started, ended = span.get("started"), span.get("ended")
    checks = [row for row in result.get("checks") or [] if isinstance(row, dict)]
    shiploop = result.get("shiploop") or {}
    committed = result.get("committed") or {}
    reviews = metrics.get("improve_reviews") or {}
    trace = metrics.get("run_trace") or {}
    environment = result.get("environment") or {}
    left = result.get("left_behind") or {}
    row: dict = {
        "name": out.name, "case": result.get("case"), "host": result.get("host"), "model": result.get("model"),
        "effort": result.get("effort"), "pass": result.get("pass"), "outcome": result.get("outcome_class"),
        "basis": result.get("outcome_basis"),
        "verdicts": {name: (result.get(name) or {}).get("pass") for name in VERDICTS},
        "checks_passed": sum(1 for check in checks if check.get("pass")), "checks": len(checks),
        "failed_checks": [{"command": tilde(check.get("command"))[-90:],
                           "output_end": " ".join(tilde(check.get("output") or "").split())[-260:]}
                          for check in checks if not check.get("pass")],
        "versions": result.get("versions"), "boundary": result.get("boundary"), "host_build": result.get("host_build"),
        "started": clock(started), "ended": clock(ended),
        "minutes": round((ended - started) / 60, 1) if started and ended else None,
        "turns": metrics.get("turns"), "model_calls": metrics.get("model_calls"),
        "output_tokens": (metrics.get("tokens") or {}).get("output"), "cost_usd": metrics.get("cost_usd"),
        "sessions": (result.get("process") or {}).get("sessions") and len(result["process"]["sessions"]),
        "resumes": (result.get("process") or {}).get("resumes"),
        "engine": {"status": shiploop.get("status"), "stage": shiploop.get("stage"),
                   "revision": shiploop.get("revision"), "report_html": shiploop.get("report_html"),
                   "runs": shiploop.get("runs")},
        "reviews": {"children": reviews.get("children"), "passes": reviews.get("passes"),
                    "changed_something": reviews.get("edited_children")},
        "trace": {key: trace.get(key) for key in ("commands", "refusals", "checks_failed", "crashed")},
        "gate_counts": metrics.get("gate_counts"),
        "committed": {"pass": committed.get("pass"), "head": committed.get("head"),
                      "uncommitted": len(committed.get("uncommitted") or [])},
        "left_behind": {"observed": left.get("observed"), "reaped": len(left.get("reaped") or []),
                        "survived": len(left.get("survived") or [])},
        "load": {"start": (environment.get("start") or {}).get("loadavg"),
                 "end": (environment.get("end") or {}).get("loadavg")},
        "last_message": last_message(out),
        "return_kind": (((metrics.get("fidelity") or {}).get("validation") or {}).get("release_verify") or {}).get("kind"),
    }
    run = Path(str(shiploop.get("run_dir") or load(out / "shiploop-run.json").get("run_dir") or ""))
    row["harness_reason"] = tilde(shiploop.get("reason")) if shiploop.get("reason") else None
    if not (run / "state.md").is_file():
        # The harness names no run when the session started ShipLoop more than once.  Read the run that went furthest
        # and say so; the harness's own verdict stands as it was written.
        started = sorted((path.parent for path in out.glob(".shiploop-runs/*/run/state.md")),
                         key=lambda path: len(record(path / "state.md").get("history") or []))
        if started:
            run = started[-1]
            row["run_read"] = (f"the harness names no run ({len(started)} run folders); read here: the one with the "
                               f"longest history, {run.parent.name}")
            state_read = record(run / "state.md")
            row["engine"].update(status=state_read.get("status"), stage=state_read.get("stage"),
                                 revision=state_read.get("revision"), report_html=(run / "report.html").is_file())
    if (run / "state.md").is_file():
        state = record(run / "state.md")
        refused = refusals(run)
        by_stage: dict[str, int] = {}
        for entry in refused:
            by_stage[str(entry["stage"])] = by_stage.get(str(entry["stage"]), 0) + 1
        row["refusals"] = {"count": len(refused), "by_stage": by_stage,
                           "naming_defaults": [entry for entry in refused if "defaults" in entry["text"]],
                           "at_release_verify": [entry["text"][:300] for entry in refused
                                                 if entry["stage"] == "release-verify"]}
        row.update(release(run, state))
        row["done_packet"] = done_packet(run)
        row["the_list"] = the_list(run, state)
    else:
        row["run"] = "no run directory"
    return row


def show(row: dict) -> None:
    print(f"== {row['name']}: {row['case']} | {row['host']} {row['model']} {row['effort']} | "
          f"{row['outcome']} ({row['basis']})")
    print(f"   verdicts {row['verdicts']} | case checks {row['checks_passed']} of {row['checks']}")
    for check in row["failed_checks"]:
        print(f"   FAILED CHECK ...{check['command']} | ...{check['output_end']}")
    versions = row.get("versions") or {}
    boundary = row.get("boundary") or {}
    print(f"   build: skill-craft {versions.get('plugin_version')} / ShipLoop {versions.get('shiploop_version')}, "
          f"source {versions.get('source')}, fingerprint {versions.get('plugin_sha256')}, commit "
          f"{versions.get('local_head')} | evaluator {boundary.get('evaluator')}, oracle {boundary.get('oracle')} | "
          f"{row['host_build']}")
    print(f"   {row['started']} to {row['ended']}, {row['minutes']} minutes | sessions {row['sessions']}, resumes "
          f"{row['resumes']} | turns {row['turns']}, model calls {row['model_calls']}, output tokens "
          f"{row['output_tokens']}, cost {row['cost_usd']}")
    engine = row["engine"]
    if row.get("harness_reason"):
        print(f"   the harness on the ShipLoop run: {row['harness_reason']}")
    if row.get("run_read"):
        print(f"   {row['run_read']}")
    print(f"   engine {engine['status']} at {engine['stage']}, revision {engine['revision']}, report "
          f"{engine['report_html']}, run folders {engine['runs']} | reviews {row['reviews']} | trace {row['trace']}")
    if "refusals" in row:
        refused = row["refusals"]
        print(f"   refused commands: {refused['count']} {refused['by_stage']} | naming defaults: "
              f"{len(refused['naming_defaults'])}")
        for entry in refused["naming_defaults"]:
            print(f"      [{entry['stage']}] {entry['text'][:260]}")
        for item in row["work_items"]:
            print(f"   work item {item['id']} ({item['title']}): {item['steps']} steps, regression commands "
                  f"{item['regression_commands']}")
        for checks in row["consumer_checks"]:
            print(f"   release-plan recorded consumer checks: {[check[:110] for check in checks]}")
        print("   release stages in order:", " ".join(row["release_stages"]))
        for attempt in row["release_verify"]:
            print(f"   release-verify {attempt['record']}: the action ended {attempt['action_ended']}; in "
                  f"{attempt['where']}; returned head {attempt['head']}; passed {attempt['passed']} "
                  f"({attempt['disposition']})")
            for run_row in attempt["runs"]:
                print(f"      {'ADDED BY SHIPLOOP' if run_row['added'] else 'check'} [{run_row['suite']}] "
                      f"{str(run_row['command'])[:100]} -> {run_row['status']}, exit {run_row['exit']}, ran "
                      f"{run_row['ran']}, {run_row['seconds']} s")
        for text in row["refusals"]["at_release_verify"]:
            print("   REFUSAL at release-verify:", text)
        listed = row["the_list"]
        print(f"   the list: recorded {listed['recorded']}, rows {listed['rows']}, rows that name a roll-back "
              f"{listed['roll_back_rows']}; next-stage packets with the block "
              f"{listed['next_stage_packets_with_the_block']}; report section {listed.get('report_section')}, right "
              f"after the request {listed.get('report_section_right_after_the_request')}")
        for number, question in enumerate(listed["questions"], 1):
            print(f"      {number}. {question}")
        print(f"   the done packet's list: {row['done_packet']}")
    else:
        print("   ", row.get("run"))
    print(f"   returned checkout: committed {row['committed']} | left behind {row['left_behind']} | load "
          f"{row['load']}")
    print("   the host's last message to the user:")
    for line in (row.get("last_message") or "(none found)").splitlines():
        print("      | " + line)


def cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(rows: list[dict]) -> str:
    """The round as one Markdown table, a column a delivery, every cell from the fields ``read`` gathered."""
    def verdicts(row: dict) -> str:
        failed = [name for name, ok in row["verdicts"].items() if not ok]
        return "all five pass" if not failed else "failed: " + ", ".join(failed)

    def checks(row: dict) -> str:
        text = f"{row['checks_passed']} of {row['checks']}"
        if row["failed_checks"]:
            names = [check["command"].split("/")[-1].replace('"', "") for check in row["failed_checks"]]
            text += "; failed: " + ", ".join(names)
        return text

    def the_list_cell(row: dict) -> str:
        listed, done = row.get("the_list") or {}, row.get("done_packet") or {}
        if not listed:
            return "no run folder read"
        return (f"{listed['rows']} rows; {listed['roll_back_rows']} name a roll-back; printed by the next stage's "
                f"packet: {'yes' if listed['next_stage_packets_with_the_block'] else 'no'}; done packet lists "
                f"{done.get('rows')}; report section right after the request: "
                f"{'yes' if listed.get('report_section_right_after_the_request') else 'no'}")

    def plan(row: dict) -> str:
        return "; ".join(f"{item['id']}: {item['steps']} steps" for item in row.get("work_items") or []) or "none read"

    def refused(row: dict) -> str:
        found = row.get("refusals") or {}
        stages = ", ".join(f"{stage} {count}" for stage, count in (found.get("by_stage") or {}).items())
        return f"{found.get('count')}" + (f" ({stages})" if stages else "") + f"; naming `defaults`: {len(found.get('naming_defaults') or [])}"

    def verify(row: dict) -> str:
        attempts = row.get("release_verify") or []
        if not attempts:
            return "no record"
        parts = [f"{len(attempts)} record(s), {len(found.get('at_release_verify') or [])} refusal(s)"
                 for found in [row.get("refusals") or {}]]
        for attempt in attempts:
            runs = "; ".join(("ADDED BY SHIPLOOP " if run["added"] else "") + f"`{str(run['command'])[:60]}` "
                             f"{run['status']}" + (f", {run['ran']} tests" if run["ran"] is not None else "")
                             for run in attempt["runs"])
            parts.append(f"in {attempt['where']}, the action ended {attempt['action_ended']}: {runs}")
        return ". ".join(parts)

    lines = [("", lambda row: f"`{row['name']}`"),
             ("Case", lambda row: f"`{row['case']}`"),
             ("Builder", lambda row: f"{row['host_build']}, {row['model']} at {row['effort']}; {row['sessions']} "
                                     f"session(s), {row['resumes']} resume(s)"),
             ("Harness verdicts (invoked, plugin, process, shiploop, committed)", verdicts),
             ("Case checks", checks),
             ("The list of defaults", the_list_cell),
             ("Step plan", plan),
             ("Start to end", lambda row: f"{row['started']} to {row['ended']}, {row['minutes']} minutes"),
             ("Accepted revisions", lambda row: row["engine"]["revision"]),
             ("Stage reviews", lambda row: f"{row['reviews']['children']} in {row['reviews']['passes']} passes; "
                                           f"{row['reviews']['changed_something']} changed something"),
             ("Refused ShipLoop commands, all recovered in the session", refused),
             ("release-verify", verify),
             ("Turns, model calls, output tokens, cost", lambda row: f"{row['turns']}, {row['model_calls']}, "
              f"{row['output_tokens']}, " + (f"${row['cost_usd']:.2f}" if row["cost_usd"] else "no figure")),
             ("Returned source", lambda row: f"committed: {'yes' if row['committed']['pass'] else 'no'}, head "
              f"`{str(row['committed']['head'])[:12]}`, {row['committed']['uncommitted']} uncommitted; return kind "
              f"{row.get('return_kind')}"),
             ("Left behind (harness)", lambda row: f"reaped {row['left_behind']['reaped']}, survived "
              f"{row['left_behind']['survived']}")]
    out = []
    for index, (label, make) in enumerate(lines):
        out.append("| " + " | ".join([label] + [cell(make(row)) for row in rows]) + " |")
        if index == 0:
            out.append("|" + "---|" * (len(rows) + 1))
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("names", nargs="*")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--table", type=Path, help="also write the round as one Markdown table to this file")
    args = parser.parse_args()
    folders = ([args.root / name for name in args.names] if args.names
               else sorted(path.parent for path in args.root.glob("*/result.json")))
    rows = []
    for folder in folders:
        if not (folder / "result.json").is_file():
            print(f"== {folder.name}: no result.json yet")
            continue
        rows.append(read(folder))
        show(rows[-1])
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    if args.table:
        args.table.write_text(table(rows), encoding="utf-8")
    sys.exit(0)


main()
