#!/usr/bin/env python3
"""Pair every shell command a headless Grok E2E run asked to run with Grok's own permission decision for it.

Read-only over the run folders. For each run folder that kept its isolated Grok profile (``home/.grok``):

- Grok's session store (``home/.grok/sessions/<scope>/<session>/events.jsonl``) records one ``permission_resolved`` event per
  tool call, with its ``decision`` (allow, cancelled, ...) and ``wait_ms``, but no tool-call id or command.
- The run's own stream (``events.jsonl``, written by run.py) records each ``tool_call`` with its ``rawInput.command`` and
  the ``tool_call_update`` "User cancelled the execution for tool `run_terminal_command`" for a refused one.

Shell calls are paired by order (the n-th ``run_terminal_command`` decision with the n-th ``run_terminal_command`` call). A
pairing is kept only when both counts match and every decision ``cancelled`` falls on a call the stream marks cancelled; a
run that fails either test is reported as unpaired and contributes only its cancelled-call commands from the stream.

Each call's ``floor_shapes`` come from the harness's own rule (test/shiploop_e2e/grok_preempt.py), the one the E2E
hook applies. The stage at a refusal is the ShipLoop stage in progress at the decision's time: the first history entry of the run's
``state.md`` whose accept time (``timeline.json``) is at or after it, else the stage the run was at when it stopped.

Usage: analyze.py OUT_DIR [--until YYYY-MM-DD] [RUN_ROOT ...]   (default roots: ~/e2e-runs*; --until keeps the runs whose
stream was last written on or before that day: the committed evidence uses 2026-11-14, the corpus of the diagnosis). Writes OUT_DIR/calls.jsonl (one row per shell
call: run, decision, wait_ms, command, stage, features) and OUT_DIR/runs.json (one row per run).
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e"))
from grok_preempt import floor_shapes  # noqa: E402  (the harness's one implementation of the rule the probes found)

SKIP = ("/fixtures/", "-source/", "/test/", "/home/", "/work/", "/delivery/", "/export/", "/review-export/")
CANCEL_TEXT = "User cancelled the execution for tool `run_terminal_command`"


def iso(ts: str) -> float:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def jsonl(path: Path):
    with open(path, errors="replace") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                yield value


def run_folders(roots: list[str]) -> list[Path]:
    found = set()
    for root in roots:
        for events in glob.glob(os.path.join(root, "**", "events.jsonl"), recursive=True):
            folder = os.path.dirname(events)
            if any(part in folder + "/" for part in SKIP):
                continue
            if "/.grok/" in folder or "/.shiploop-runs/" in folder:
                continue
            found.add(Path(folder))
    return sorted(found)


def store_decisions(folder: Path) -> tuple[list[dict], list[dict], Counter, list[float]]:
    shell, turns, all_tools, moments = [], [], Counter(), []
    for store in sorted(folder.glob("home/.grok/sessions/*/*/events.jsonl")):
        for event in jsonl(store):
            kind = event.get("type")
            if kind == "permission_resolved":
                all_tools[(event.get("tool_name"), event.get("decision"))] += 1
                moments.append(iso(event["ts"]))
                if event.get("tool_name") == "run_terminal_command":
                    shell.append({"t": iso(event["ts"]), "decision": event.get("decision"),
                                  "wait_ms": event.get("wait_ms")})
            elif kind == "turn_ended":
                turns.append({"t": iso(event["ts"]), "outcome": event.get("outcome"),
                              "category": event.get("cancellation_category")})
    shell.sort(key=lambda row: row["t"])
    turns.sort(key=lambda row: row["t"])
    return shell, turns, all_tools, sorted(moments)


def stream_calls(folder: Path) -> tuple[list[dict], set[str], bool]:
    calls, cancelled, grok = [], set(), False
    for event in jsonl(folder / "events.jsonl"):
        kind = event.get("type")
        if kind == "tool_call" and event.get("toolName") == "run_terminal_command":
            grok = True
            raw = event.get("rawInput") or {}
            calls.append({"id": event.get("toolCallId"), "command": raw.get("command") or "",
                          "description": raw.get("description") or ""})
        elif kind == "tool_call_update" and event.get("status") == "failed":
            text = json.dumps(event.get("content"))
            if CANCEL_TEXT in text:
                cancelled.add(event.get("toolCallId"))
    return calls, cancelled, grok


def shiploop_history(folder: Path) -> tuple[list[tuple[float, str]], str | None, str | None]:
    """[(accept time, stage)] for the run's accepted actions, and the stage/status it stopped at."""
    recorded = None
    marker = folder / "shiploop-run.json"
    if marker.is_file():
        try:
            data = json.loads(marker.read_text())
        except ValueError:
            data = None
        recorded = data.get("run_dir") if isinstance(data, dict) else None
    candidates = [Path(recorded)] if recorded and Path(recorded, "state.md").is_file() else []
    if not candidates:
        candidates = sorted(folder.glob("**/.shiploop-runs/*/run"), key=lambda p: (p / "state.md").stat().st_mtime
                            if (p / "state.md").is_file() else 0)[-1:]
    for run in candidates:
        try:
            text = (run / "state.md").read_text()
            state = json.loads(text[text.index("{"): text.rindex("}") + 1])
            accepted = json.loads((run / "timeline.json").read_text()).get("accepted", {})
        except (OSError, ValueError):
            continue
        rows = sorted((iso(accepted[h["action"]]), h.get("stage") or "?") for h in state.get("history", [])
                      if h.get("action") in accepted)
        return rows, state.get("stage"), state.get("status")
    return [], None, None


def stage_at(history: list[tuple[float, str]], final: str | None, moment: float) -> str:
    for accepted, stage in history:
        if accepted >= moment:
            return stage
    return final or "?"


ASSIGN = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=")


def features(command: str) -> dict:
    """Shell shapes the Grok docs name as escalating (22-permissions-and-safety.md)."""
    first = command.lstrip().split("\n", 1)[0]
    return {
        "multiline": "\n" in command.strip(),
        "starts_assign": bool(ASSIGN.match(command)),
        "has_assign": bool(re.search(r"(^|[\s;&|(])[A-Za-z_][A-Za-z0-9_]*=", command)),
        "var_ref": bool(re.search(r"\$[A-Za-z_{]", command)),
        "starts_cd": first.startswith("cd "),
        "has_cd": bool(re.search(r"(^|&&|;|\n)\s*cd\s", command)),
        "heredoc": "<<" in command,
        "cmd_subst": "$(" in command or "`" in command,
        "redirect": bool(re.search(r"[^<>&]>[^&]|>>", command)),
        "python_c": bool(re.search(r"\bpython3?\s+-c\b", command)),
        "python_stdin": bool(re.search(r"\bpython3?\s+-\s", command + " ")),
        "node_e": bool(re.search(r"\bnode\s+(-e|--eval|--input-type)", command)),
        "set_e": bool(re.search(r"(^|\n)\s*set -", command)),
        "control_flow": bool(re.search(r"(^|[;\n&|])\s*(for|while|if|case|until)\s", command)),
        "subshell": bool(re.search(r"(^|[;&|\n])\s*\(", command)),
        "background": bool(re.search(r"[^&]&\s*($|\n)", command)),
        "pipe": bool(re.search(r"[^|]\|[^|]", command)),
        "and_chain": "&&" in command,
        "length": len(command),
    }


def launches(folder: Path) -> list[dict]:
    """Every launch's host, model, effort, permission mode and allow rules, from invocation*.json (run.py writes one per
    launch; Codex streams are translated into Grok's event shape, so the stream alone does not name the host)."""
    found = []
    for path in sorted(folder.glob("invocation*.json")):
        try:
            data = json.loads(path.read_text())
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        argv = data.get("argv") or []
        mode = argv[argv.index("--permission-mode") + 1] if "--permission-mode" in argv else None
        if not argv and data.get("kind") == "step-slice":
            mode = "auto"  # slice.py records no argv; its --permission-mode default is auto, and no slice command overrode it
        allow = [argv[i + 1] for i, word in enumerate(argv[:-1]) if word == "--allow"]
        found.append({"file": path.name, "host": data.get("host") or (Path(argv[0]).name if argv else None),
                      "model": data.get("model"), "effort": data.get("effort"), "build": data.get("host_build"),
                      "mode": mode, "always_approve": "--always-approve" in argv or "--yolo" in argv, "allow": allow})
    return found


def session_cwd(folder: Path) -> str | None:
    """The working directory Grok's session ran in: its store's scope folder is that path, URL-encoded."""
    scopes = [p.name for p in folder.glob("home/.grok/sessions/*") if p.is_dir()]
    return urllib.parse.unquote(scopes[0]) if len(scopes) == 1 else None


def logged_builds(folder: Path) -> list[str]:
    """The Grok builds the profile's own log names (``ver`` on each line), for runs that recorded no host_build."""
    found = []
    log = folder / "home" / ".grok" / "logs" / "unified.jsonl"
    if log.is_file():
        for event in jsonl(log):
            version = event.get("ver")
            if version and version not in found:
                found.append(version)
    return found


def run_info(folder: Path) -> dict:
    for name in ("result.json", "slice-result.json"):
        path = folder / name
        if path.is_file():
            try:
                data = json.loads(path.read_text())
            except ValueError:
                continue
            proc = data.get("process") or {}
            sessions = proc.get("sessions") or data.get("sessions") or []
            return {"source": name, "case": data.get("case"), "model": data.get("model"), "effort": data.get("effort"),
                    "build": data.get("host_build"), "outcome": data.get("outcome_class"), "pass": data.get("pass"),
                    "shiploop_status": (data.get("shiploop") or {}).get("status") or data.get("run_status"),
                    "sessions": len(sessions) if isinstance(sessions, list) else None,
                    "cancelled_sessions": sum(1 for s in sessions if isinstance(s, dict) and s.get("stop") == "cancelled")
                    if isinstance(sessions, list) else None,
                    "cost_usd": (data.get("cli") or {}).get("cost_usd"),
                    "resume_stop": (data.get("termination") or {}).get("resume_stop"),
                    "stage": (data.get("shiploop") or {}).get("stage") or data.get("stage_at_stop"),
                    "seconds": round(sum(s.get("elapsed_seconds") or 0 for s in sessions if isinstance(s, dict)), 1)
                    if isinstance(sessions, list) else None}
    return {"source": None}


def main() -> int:
    arguments = sys.argv[1:]
    out = Path(arguments.pop(0))
    until = None
    if arguments[:1] == ["--until"]:
        until = arguments[1]
        arguments = arguments[2:]
    roots = arguments or sorted(glob.glob(os.path.expanduser("~/e2e-runs*")))
    out.mkdir(parents=True, exist_ok=True)
    runs, rows = [], []
    for folder in run_folders(roots):
        if until and dt.datetime.fromtimestamp((folder / "events.jsonl").stat().st_mtime).strftime("%Y-%m-%d") > until:
            continue  # written after the corpus closed (a live run, or one started after the diagnosis)
        started = launches(folder)
        if not started or any(launch["host"] != "grok" for launch in started):
            continue  # not a Grok run, or a mixed-host run
        calls, cancelled_ids, grok = stream_calls(folder)
        if not grok:
            continue
        decisions, turns, all_tools, moments = store_decisions(folder)
        history, final_stage, final_status = shiploop_history(folder)
        paired = (bool(decisions) and len(decisions) == len(calls)
                  and all(call["id"] in cancelled_ids for call, d in zip(calls, decisions) if d["decision"] == "cancelled")
                  and sum(d["decision"] == "cancelled" for d in decisions) == len(cancelled_ids))
        info = run_info(folder)
        mtime = (folder / "events.jsonl").stat().st_mtime
        first = started[0]
        cwd = session_cwd(folder)
        run = {"run": str(folder), "date": dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"), **info,
               "cwd": cwd, "logged_builds": logged_builds(folder),
               "model": info.get("model") or first["model"], "effort": info.get("effort") or first["effort"],
               "build": info.get("build") or first["build"], "modes": sorted({str(l["mode"]) for l in started}),
               "always_approve": any(l["always_approve"] for l in started),
               "allow": sorted({rule for l in started for rule in l["allow"]}), "launches": len(started),
               "shell_calls": len(calls), "refused_stream": len(cancelled_ids), "store": bool(decisions),
               "paired": paired, "decisions": {f"{t}:{d}": n for (t, d), n in sorted(all_tools.items(), key=str)},
               "turns_ended": Counter(f"{t['outcome']}:{t['category']}" for t in turns),
               "final_stage": final_stage, "final_status": final_status}
        runs.append(run)
        for index, call in enumerate(calls):
            decision = decisions[index] if paired else None
            refused = call["id"] in cancelled_ids
            if not paired and not refused:
                continue  # an unpaired run contributes only what its stream proves: its refused commands
            moment = decision["t"] if decision else None
            # A refusal ends the host session: the next permission decision of any tool is the next session's first call.
            following = next((m for m in moments if moment is not None and m > moment + 0.5), None) if refused else None
            rows.append({"run": str(folder), "index": index, "refused": refused, "t": moment,
                         "restart_gap_s": round(following - moment, 1) if following else None,
                         "decision": decision["decision"] if decision else ("cancelled" if refused else None),
                         "wait_ms": decision["wait_ms"] if decision else None,
                         "stage": stage_at(history, final_stage, moment) if moment else None,
                         "command": call["command"], "description": call["description"],
                         "floor_shapes": floor_shapes(call["command"], cwd), **features(call["command"])})
    with open(out / "calls.jsonl", "w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    (out / "runs.json").write_text(json.dumps(runs, indent=1, default=dict))
    print(f"{len(runs)} Grok runs, {sum(r['paired'] for r in runs)} paired, {len(rows)} call rows "
          f"({sum(r['refused'] for r in rows)} refused)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
