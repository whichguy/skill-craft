#!/usr/bin/env python3
"""Callback failures across the 1003 batch: a frozen, one-time analysis (stdlib only, no model call).

Backs test/shiploop_e2e/LEARNINGS.md, "Callback path typos across the 1003 batch". Frozen 2026-10-04; superseded by
metrics.collect once the planned metrics item M1 (Claude-shaped failure counting) lands. Do not extend it.

It reads each run's events.jsonl (Claude stream-json, and the ACP-style Codex/Grok stream), keeps every ShipLoop or
Until Loop command, and calls a command failed on a nonzero exit (or is_error). A failed command gets one class, keyed
on the typed command or on line-anchored output text, never on a substring anywhere in the output: space_in_path,
until_loop_script_path, bare_shiploop_cli, older_cache_refusal, content_refusal, other. Recovery is the host tool calls
from the failure to the next successful command of the same verb (+1 is the very next call) and the seconds between
them, for the path and harness classes. Each run is split into sessions at its invocation-resume-<host>-<epoch>.json
files; typed paths (path tokens under the runs root in every typed command, heredoc text included), callbacks and
space-in-path typos are counted per session. A refusal line behind exit 0 (a pipe, a wrapper script) is counted apart,
not as a failure, so the Claude failure counts are lower bounds.

  callback_failures.py --root /Users/dadleet/e2e-runs --out failures.json                       # cutoffs = line counts now
  callback_failures.py --root /Users/dadleet/e2e-runs --cutoffs failures.json --out again.json  # cmp again.json failures.json

A cutoff is a count of newline-terminated events.jsonl lines; only lines below it are read, so a live run's growth
does not change the result.
"""
import argparse, bisect, json, math, re
from pathlib import Path

E2E_ROOT = "/Users/dadleet/e2e-runs"  # the path the commands typed, wherever --root points now
BOUNDARY = "/20261003/v1161-"        # the run-name boundary the run-name hypothesis blamed
CHARS = r"[^\s\"'<>|;&)(`$]*"
TOKEN = re.compile(re.escape(E2E_ROOT) + "/" + CHARS)
SPACED = re.compile(re.escape(E2E_ROOT) + "/" + CHARS + r"/ +[\w.-]+")
CLI = re.compile(r"(?:^|[\s\"'=/])(?:shiploop|\$\{?[A-Za-z_]*(?:CLI|SHIPLOOP|SL)[A-Za-z_]*\}?)[\"']?\s+(?P<verb>[a-z][\w-]*)")
UNTIL = re.compile(r"(?:until_loop\w*\.py|\$\{?[A-Za-z_]*(?:UNTIL|UL|LOOP)[A-Za-z_]*\}?)[\"']?\s+(?P<verb>[a-z][\w-]*)")
VERBS = {"complete", "next", "resume", "init", "workspace", "lint", "status", "report", "context", "halt", "pause",
         "chain", "view", "hook-status", "graph-dry-run", "delegation", "lint-mode", "improve-bind", "improve-start",
         "improve-commit", "improve-complete", "improve-reconcile", "backchain-check"}
CALLBACKS = {"complete", "improve-bind", "improve-start", "improve-commit", "improve-complete", "improve-reconcile"}
EXIT = re.compile(r"^Exit code (\d+)")
REFUSAL = re.compile(r"^ShipLoop (?:navigator|blocked): ", re.M)
OLDER_CACHE = re.compile(r"^ShipLoop blocked: saved run state cannot be loaded", re.M)
NO_CLI = re.compile(r"^[^\s:]+:\d+: command not found: shiploop\s*$", re.M)
BAD_SCRIPT = re.compile(r"^\S+: can't open file '(?P<p>[^']*until_loop\w*\.py)'", re.M)
ACTION = re.compile(r"--action=\"?(nav-[0-9a-f]{32})")
HARNESS = re.compile(r"marketplace|plugin_cli|/\.codex/")
VAR_RUN_DIR = re.compile(r"--run-dir[= ]\"?\$")
COMPLETE_ACTION = re.compile(r"complete.*--action", re.S)


def update_text(e, raw):
    """The visible text of an ACP tool_call_update: its content blocks, then rawOutput.output_for_prompt."""
    parts = []
    for p in e.get("content") or []:
        inner = p.get("content") if isinstance(p, dict) else None
        parts.append(inner.get("text", "") if isinstance(inner, dict) else inner if isinstance(inner, str) else "")
    parts.append(raw.get("output_for_prompt") or "")
    return "\n".join(x for x in parts if isinstance(x, str) and x)


def commands(path, cutoff):
    """Every host command in the first `cutoff` lines: {n (0-based event line), order, cmd, out, failed, kind, verb}."""
    calls, retired, order = {}, [], 0
    with open(path, "rb") as f:
        for n, line in enumerate(f):
            if n >= cutoff:
                break
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = e.get("type")
            if t == "assistant":
                for b in (e.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        order += 1
                        calls[b["id"]] = {"n": n, "order": order, "cmd": str((b.get("input") or {}).get("command") or "")}
            elif t == "user":
                for b in (e.get("message") or {}).get("content") or []:
                    c = calls.get(b.get("tool_use_id")) if isinstance(b, dict) and b.get("type") == "tool_result" else None
                    if c:
                        text = b.get("content")
                        if isinstance(text, list):
                            text = "".join(str(p.get("text") or "") for p in text if isinstance(p, dict))
                        m = EXIT.match(str(text or ""))
                        c.update(out=str(text or ""), failed=bool(b.get("is_error")) or (m is not None and int(m[1]) != 0))
            elif t == "tool_call":
                order += 1
                if e.get("toolCallId") in calls:  # ids restart in a resumed session
                    retired.append(calls.pop(e["toolCallId"]))
                arg = e.get("rawInput") if isinstance(e.get("rawInput"), dict) else {}
                calls[e.get("toolCallId")] = {"n": n, "order": order, "cmd": str(arg.get("command") or "")}
            elif t == "tool_call_update" and e.get("status") in ("completed", "failed"):
                c = calls.get(e.get("toolCallId"))
                if c and "failed" not in c:
                    raw = e.get("rawOutput") if isinstance(e.get("rawOutput"), dict) else {}
                    c.update(out=update_text(e, raw), failed=raw.get("exit_code") not in (None, 0) or e.get("status") == "failed")
    out = sorted(list(calls.values()) + retired, key=lambda c: c["order"])
    for c in out:
        m, u = CLI.search(c["cmd"]), UNTIL.search(c["cmd"])
        c["kind"], c["verb"] = ("shiploop", m["verb"]) if m and m["verb"] in VERBS else ("until-loop", u["verb"]) if u else (None, None)
    return out


def classify(c):
    """(class, path tail): the typed command first, then line-anchored output text."""
    out = c.get("out") or ""
    if (s := SPACED.search(c["cmd"])):
        return "space_in_path", s[0][-80:]
    if (b := BAD_SCRIPT.search(out)):
        return "until_loop_script_path", b["p"][-80:]
    if NO_CLI.search(out):
        return "bare_shiploop_cli", ""
    if OLDER_CACHE.search(out):
        return "older_cache_refusal", ""
    return ("content_refusal" if REFUSAL.search(out) else "other"), ""


def recovery(cmds, i, cls, when):
    c = cmds[i]
    if cls in ("content_refusal", "other"):
        return None, None
    act = ACTION.search(c["cmd"])
    for q in cmds[i + 1:]:
        if not q["kind"] or q.get("failed") is not False:
            continue
        if cls in ("bare_shiploop_cli", "older_cache_refusal"):
            hit = q["verb"] == "next" and HARNESS.search(q["cmd"])
        else:
            qa = ACTION.search(q["cmd"])
            hit = (q["kind"], q["verb"]) == (c["kind"], c["verb"]) and (act is None or q["kind"] == "until-loop" or (qa and qa[1] == act[1]))
        if hit:
            t0, t1 = when(c["n"]), when(q["n"])
            return q["order"] - c["order"], round(t1 - t0, 1) if t0 and t1 else None
    return None, None


def p_later(typos, late_typos, late, total):
    """One-sided hypergeometric P(at least `late_typos` of `typos` fall among the `late` of `total` typings)."""
    hit = sum(math.comb(late, x) * math.comb(total - late, typos - x) for x in range(late_typos, typos + 1))
    return round(hit / math.comb(total, typos), 4) if typos else None


def segment(cmds, lo, hi, when, t0):
    part = [c for c in cmds if lo <= c["n"] < hi and c["cmd"]]
    paths = [len(TOKEN.findall(c["cmd"])) for c in part]
    typo = [i for i, c in enumerate(part) if SPACED.search(c["cmd"])]
    before, last = [], 0  # path tokens from the previous typo command (inclusive) up to this one
    for i in typo:
        before.append(sum(paths[last:i]))
        last = i
    cb = [c for c in part if c["kind"] == "shiploop" and c["verb"] in CALLBACKS]
    return {"start": lo, "end": hi, "commands": len(part), "callbacks": len(cb), "typed_paths": sum(paths),
            "boundary_typings": sum(c["cmd"].count(BOUNDARY) for c in part),
            "typo_commands": len(typo), "callback_typos": sum(1 for c in cb if SPACED.search(c["cmd"])),
            "broken_commands": sum(1 for i in typo if part[i]["kind"] and part[i]["failed"]), "typo_events": [part[i]["n"] for i in typo],
            "typo_hours": [round((when(part[i]["n"]) - t0) / 3600, 2) for i in typo], "typings_before_each_typo": before,
            "typings_since_last_typo": sum(paths[last:]) if typo else None,
            "callbacks_since_last_typo": sum(1 for c in cb if c["n"] > part[typo[-1]]["n"]) if typo else None}


def analyse(root, run_dir, cutoff):
    rel = str(run_dir.relative_to(root))
    cmds = commands(run_dir / "events.jsonl", cutoff)
    tl = [json.loads(x) for x in (run_dir / "timeline.jsonl").read_text().splitlines() if x.strip()]
    lines, secs = [int(d["line"]) for d in tl], [float(d["t"]) for d in tl]
    when = lambda n: secs[min(bisect.bisect_left(lines, n), len(secs) - 1)] if secs else None
    res = json.loads((run_dir / "result.json").read_text())
    epochs = sorted(int(m[1]) for p in run_dir.glob("invocation-resume-*.json") if (m := re.search(r"-(\d+)\.json$", p.name)))
    cuts = [0] + [lines[min(bisect.bisect_left(secs, e), len(lines) - 1)] for e in epochs] + [cutoff]
    rows, classes = [], {}
    for i, c in enumerate(cmds):
        if c.get("failed") and c["kind"]:
            cls, tail = classify(c)
            calls, seconds = recovery(cmds, i, cls, when)
            classes[cls] = classes.get(cls, 0) + 1
            rows.append({"run": rel, "event": c["n"], "verb": f"{c['kind']} {c['verb']}", "class": cls,
                         "recovery_calls": calls, "seconds": seconds, "path_tail": tail})
    exit0 = [c for c in cmds if c.get("failed") is False and REFUSAL.search(c.get("out") or "")]
    complete = [c for c in cmds if c["kind"] == "shiploop" and c["verb"] == "complete"]
    wsroot = next((run_dir / ".shiploop-runs").glob("*")).name
    sessions = [segment(cmds, lo, hi, when, secs[0]) for lo, hi in zip(cuts, cuts[1:])]
    s = {"run": rel, "host": res["host"], "model": res["model"], "plugin": res["versions"]["plugin_version"], "cutoff": cutoff,
         "result_path_len": len(f"{E2E_ROOT}/{rel}/.shiploop-runs/{wsroot}/run/inbox/nav-{'0' * 32}.md"),
         "shiploop_commands": sum(1 for c in cmds if c["kind"] == "shiploop"),
         "until_loop_commands": sum(1 for c in cmds if c["kind"] == "until-loop"),
         "callbacks": sum(x["callbacks"] for x in sessions), "typed_paths": sum(x["typed_paths"] for x in sessions),
         "complete_commands": len(complete), "complete_variable_run_dir": sum(1 for c in complete if VAR_RUN_DIR.search(c["cmd"])),
         "complete_action_commands": sum(1 for c in cmds if COMPLETE_ACTION.search(c["cmd"])),
         "failed": len(rows), "classes": classes, "exit0_refusals": sum(1 for c in exit0 if c["kind"]),
         "exit0_refusals_any_command": len(exit0), "sessions": sessions}
    k, kc = (sum(x[key] for x in sessions) for key in ("typo_commands", "callback_typos"))
    if len(sessions) > 1 and k:
        late = lambda key: sum(x[key] for x in sessions[1:])
        s["later_sessions_p"] = {"typings": p_later(k, late("typo_commands"), late("typed_paths"), s["typed_paths"]),
                                 "callbacks": p_later(kc, late("callback_typos"), late("callbacks"), s["callbacks"])}
    return rows, s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(E2E_ROOT))
    ap.add_argument("--cutoffs", type=Path, help="a failures.json whose per-run cutoffs to reuse")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fixed = {r["run"]: r["cutoff"] for r in json.loads(a.cutoffs.read_text())["runs"]} if a.cutoffs else {}
    rows, runs, by_host, classes = [], [], {}, {}
    for ev in sorted(a.root.rglob("events.jsonl")):
        rel = str(ev.parent.relative_to(a.root))
        cutoff = fixed.get(rel)
        if cutoff is None:
            with open(ev, "rb") as f:
                cutoff = sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))
        r, s = analyse(a.root, ev.parent, cutoff)
        rows += r
        runs.append(s)
        h = by_host.setdefault("claude" if s["host"] == "claude" else f"{s['host']} {s['model']} {s['plugin']}", {})
        for key, v in (("runs", 1), ("failed", s["failed"]), ("callbacks", s["callbacks"]), ("typed_paths", s["typed_paths"]),
                       ("exit0_refusals", s["exit0_refusals"]), ("exit0_refusals_any_command", s["exit0_refusals_any_command"]),
                       ("callback_typos", sum(x["callback_typos"] for x in s["sessions"]))):
            h[key] = h.get(key, 0) + v
    for r in rows:
        classes[r["class"]] = classes.get(r["class"], 0) + 1
    head = {"failed_total": len(rows), "classes": classes, "by_host": by_host}
    lines = [f'  "{k}": {json.dumps(v, sort_keys=True)}' for k, v in head.items()]
    for key, items in (("runs", runs), ("rows", rows)):
        lines.append(f'  "{key}": [\n' + ",\n".join("    " + json.dumps(x, sort_keys=True) for x in items) + "\n  ]")
    a.out.write_text("{\n" + ",\n".join(lines) + "\n}\n")


main()
