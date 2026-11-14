#!/usr/bin/env python3
"""calibrate.py: the scorer and the kit against runs with known answers, before any model call.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README). Each cell is one measure of one
synthetic run whose answer follows from its construction (so the scorer is checked, not the model). A second part runs
the real kit with simulated agents at a small time scale. Exit 0 only when no cell is off.

  python3 calibrate.py          prints every cell, then "cells: N, off: K"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402
import score  # noqa: E402

T0 = 1_800_000_000.0
KIND_ORDER = {"init": 0, "end": 1, "fail": 1, "refused": 2, "claim": 3, "start": 4}


def plan_of(name: str) -> dict:
    return json.loads((HERE / "plans" / f"{name}.json").read_text())


def make_run(tmp: Path, plan: dict, schedule: dict, extras=(), failed=()) -> dagkit.Run:
    """A run directory whose ledger follows ``schedule`` {step: (start, end|None)} (offsets in seconds)."""
    run = dagkit.Run(tmp)
    (tmp / "out").mkdir(parents=True)
    text = json.dumps(plan)
    (tmp / "plan.json").write_text(text)
    plan_sha = dagkit._sha(text)
    (tmp / "meta.json").write_text(json.dumps({"schema": dagkit.SCHEMA, "plan_sha": plan_sha, "plan": plan["name"], "scale": 1}))
    rows = [(0.0, "init", None, {"scale": 1})]
    shas: dict = {}
    for s in plan["steps"]:
        i = s["id"]
        if i not in schedule:
            continue
        start, end = schedule[i]
        inputs = {d: shas.get(d) for d in s["deps"]}
        rows.append((start, "start", i, {"deps": inputs, "scale": 1}))
        if end is not None and i in failed:
            rows.append((end, "fail", i, {"reason": "injected failure"}))
        elif end is not None:
            shas[i] = dagkit.out_hash(plan_sha, i, inputs)
            rows.append((end, "end", i, {"sha": shas[i]}))
            (tmp / "out" / f"{i}.json").write_text(json.dumps({"step": i, "inputs": inputs, "sha": shas[i]}))
    rows += [(t, kind, step, detail) for t, kind, step, detail in extras]
    rows.sort(key=lambda r: (r[0], KIND_ORDER.get(r[1], 5)))
    with open(run.ledger, "w") as handle:
        for n, (t, kind, step, detail) in enumerate(rows, 1):
            handle.write(json.dumps({"seq": n, "ts": T0 + t, "at": "", "kind": kind, "step": step, "pid": 1, "ppid": 0,
                                     "detail": detail}) + "\n")
    return run


RAGGED = {"serial": {"S2": (0, 10), "S3": (10, 20), "S1": (20, 60), "S5": (60, 90), "S4": (90, 110), "S6": (110, 120)},
          "refill": {"S1": (0, 40), "S2": (0, 10), "S5": (0, 30), "S3": (10, 20), "S4": (40, 60), "S6": (60, 70)},
          "wave": {"S1": (0, 40), "S2": (0, 10), "S5": (0, 30), "S3": (40, 50), "S4": (50, 70), "S6": (70, 80)}}

CASES = [
    # name, plan, schedule, extras, failed, claim, expected measures
    ("ragged6 serial", "ragged6", RAGGED["serial"], (), (), None,
     {"makespan_s": 120.0, "peak_concurrency": 1, "independent_pairs": 6, "pairs_overlapped": 0, "refused": 0,
      "starts_before_dep_end": 0, "steps_started_twice": 0, "steps_without_end": 0, "verify": "OK", "refill": False,
      "critical_path_declared_s": 70, "serial_sum_declared_s": 120}),
    ("ragged6 ideal refill", "ragged6", RAGGED["refill"], (), (), None,
     {"makespan_s": 70.0, "peak_concurrency": 3, "pairs_overlapped": 5, "refused": 0, "starts_before_dep_end": 0,
      "verify": "OK", "refill": True}),
    ("ragged6 wave", "ragged6", RAGGED["wave"], (), (), None,
     {"makespan_s": 80.0, "peak_concurrency": 3, "pairs_overlapped": 3, "verify": "OK", "refill": False}),
    ("ragged6 premature start refused", "ragged6", RAGGED["refill"], [(5.0, "refused", "S4", {"reason": "deps"})], (), None,
     {"refused": 1, "starts_before_dep_end": 0, "verify": "OK"}),
    ("ragged6 start before dependencies end", "ragged6", {**RAGGED["refill"], "S4": (15, 35)}, (), (), None,
     {"starts_before_dep_end": 2, "verify": "FAIL"}),
    ("ragged6 step started twice", "ragged6", RAGGED["refill"], [(5.0, "start", "S2", {"deps": {}, "scale": 1})], (), None,
     {"steps_started_twice": 1, "verify": "FAIL"}),
    ("ragged6 step never ended", "ragged6", {k: v for k, v in {**RAGGED["refill"], "S5": (0, None)}.items() if k != "S6"}, (), (), None,
     {"steps_without_end": 1, "verify": "FAIL", "ended": 4}),
    ("fan4 parallel", "fan4", {f"S{n}": (0, 30) for n in range(1, 5)}, (), (), None,
     {"makespan_s": 30.0, "peak_concurrency": 4, "independent_pairs": 6, "pairs_overlapped": 6, "verify": "OK"}),
    ("fan4 serial", "fan4", {f"S{n}": (30 * (n - 1), 30 * n) for n in range(1, 5)}, (), (), None,
     {"makespan_s": 120.0, "peak_concurrency": 1, "pairs_overlapped": 0, "verify": "OK"}),
    ("chain4 serial", "chain4", {f"S{n}": (20 * (n - 1), 20 * n) for n in range(1, 5)}, (), (), None,
     {"makespan_s": 80.0, "peak_concurrency": 1, "independent_pairs": 0, "critical_path_declared_s": 80, "verify": "OK"}),
    ("fail5 correct report", "fail5", {"S1": (0, 20), "S2": (0, 20), "S3": (20, 30), "S4": (20, 30)}, (), ("S3",),
     {"done": ["S1", "S2", "S4"], "failed": ["S3"], "not_run": ["S5"]},
     {"verify": "PARTIAL", "fidelity_ok": True, "steps_without_end": 0}),
    ("fail5 false report", "fail5", {"S1": (0, 20), "S2": (0, 20), "S3": (20, 30), "S4": (20, 30)}, (), ("S3",),
     {"done": ["S1", "S2", "S4", "S5"], "failed": ["S3"], "not_run": []},
     {"verify": "PARTIAL", "fidelity_ok": False, "false_done": ["S5"], "missed_not_run": ["S5"]}),
    ("ragged6 no report", "ragged6", RAGGED["refill"], (), (), None, {"fidelity_ok": False, "final_found": False}),
]


def check(cases: list) -> tuple[int, int, list]:
    cells = off = 0
    lines = []
    with tempfile.TemporaryDirectory() as root:
        for n, (name, plan_name, schedule, extras, failed, claim, expect) in enumerate(cases):
            plan = plan_of(plan_name)
            run = make_run(Path(root) / f"c{n}", plan, schedule, extras, failed)
            m = score.ledger_measures(plan, run.events(), run)
            m.update(score.fidelity(m, claim))
            for key, want in expect.items():
                got = m.get(key)
                cells += 1
                bad = got != want
                off += bad
                lines.append(f"{'OFF' if bad else 'ok ':<3} {name:<42} {key:<24} want {want!r:<22} got {got!r}")
    return cells, off, lines


def view_cells() -> tuple[int, int, list]:
    """The host-event readers on hand-made lines in the shapes the hosts are known to emit (extended after E1)."""
    cells = off = 0
    lines = []

    def cell(name, got, want):
        nonlocal cells, off
        cells += 1
        bad = got != want
        off += bad
        lines.append(f"{'OFF' if bad else 'ok ':<3} {'events':<42} {name:<24} want {want!r:<22} got {got!r}")
    recs = [
        {"recv": 1.0, "ev": {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "toolu_1", "name": "Agent", "input": {"description": "run S1", "prompt": "python3 k run"}},
            {"type": "tool_use", "id": "toolu_2", "name": "Agent", "input": {"description": "run S2", "prompt": "python3 k run"}}],
            "usage": {"input_tokens": 10, "cache_read_input_tokens": 90}}, "parent_tool_use_id": None}},
        {"recv": 2.0, "ev": {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "toolu_3", "name": "Bash", "input": {"command": "python3 dagkit.py run --run r --step S1"}}]},
            "parent_tool_use_id": "toolu_1"}},
        {"recv": 9.0, "ev": {"type": "result", "result": "done\nFINAL {\"done\":[\"S1\"],\"failed\":[],\"not_run\":[]}",
                             "usage": {"input_tokens": 100, "output_tokens": 7, "cache_read_input_tokens": 900}, "total_cost_usd": 0.5}},
    ]
    view = [i for r in recs for i in score.normalize("claude", r)]
    cell("claude spawns", sum(1 for i in view if i["kind"] == "spawn"), 2)
    cell("claude attributed run call", [i["actor"] for i in view if i["kind"] == "call"], ["agent:oolu_1"])
    cell("claude FINAL parsed", score.final_claim(view), {"done": ["S1"], "failed": [], "not_run": []})
    cell("claude tokens input", score.tokens(view, "claude")["input"], 100)
    cell("claude tokens peak parent", score.tokens(view, "claude")["peak_parent_input"], 100)
    codex = [
        {"recv": 1.0, "ev": {"type": "item.started", "item": {"id": "item_1", "type": "collab_tool_call", "tool": "spawn_agent",
                                                              "sender_thread_id": "t0", "receiver_thread_ids": [], "prompt": "run S1"}}},
        {"recv": 1.5, "ev": {"type": "item.completed", "item": {"id": "item_1", "type": "collab_tool_call", "tool": "spawn_agent",
                                                                "receiver_thread_ids": ["t1"], "status": "completed"}}},
        {"recv": 2.0, "ev": {"type": "item.started", "item": {"id": "item_2", "type": "collab_tool_call", "tool": "wait"}}},
        {"recv": 9.0, "ev": {"type": "item.completed", "item": {"id": "item_2", "type": "collab_tool_call", "tool": "wait", "status": "completed"}}},
        {"recv": 9.5, "ev": {"type": "item.started", "item": {"id": "item_3", "type": "command_execution", "command": "python3 dagkit.py verify"}}},
        {"recv": 10.0, "ev": {"type": "item.completed", "item": {"id": "item_4", "type": "agent_message",
                                                                 "text": "FINAL {\"done\":[\"S1\"],\"failed\":[],\"not_run\":[]}"}}},
    ]
    cview = [i for r in codex for i in score.normalize("codex", r)]
    cell("codex kinds in order", [i["kind"] for i in cview], ["spawn", "result", "wait", "return", "call", "text"])
    cell("codex wait is not a spawn", sum(1 for i in cview if i["kind"] == "spawn"), 1)
    cell("codex FINAL parsed", score.final_claim(cview), {"done": ["S1"], "failed": [], "not_run": []})
    shell = [{"t": 1.0, "actor": "parent", "kind": "call", "name": "Bash", "text": "for s in S1 S2; do python3 dagkit.py run --run r --step $s & done; wait"}]
    cell("mechanism shell-parallel", score.mechanism(shell, {"peak_concurrency": 2})["kind"], "shell-parallel")
    cell("mechanism serial", score.mechanism([], {"peak_concurrency": 1})["kind"], "serial")
    return cells, off, lines


def kit_end_to_end() -> tuple[int, int, list]:
    """The real kit at PPE_TIME_SCALE 0.05: simulated agents are threads that claim, then run, with a refilling loop."""
    cells = off = 0
    lines = []
    env = dict(os.environ, PPE_TIME_SCALE="0.05")
    kit = [sys.executable, str(HERE / "dagkit.py")]
    with tempfile.TemporaryDirectory() as root:
        run_dir = Path(root) / "run"
        subprocess.run(kit + ["init", "--plan", str(HERE / "plans" / "ragged6.json"), "--run", str(run_dir)], env=env, check=True,
                       capture_output=True)
        premature = subprocess.run(kit + ["run", "--run", str(run_dir), "--step", "S4"], env=env, capture_output=True, text=True)
        workers: list = []

        def launch(step):
            thread = threading.Thread(target=lambda: subprocess.run(kit + ["run", "--run", str(run_dir), "--step", step], env=env,
                                                                    capture_output=True))
            thread.start()
            workers.append(thread)
        while True:
            ready = json.loads(subprocess.run(kit + ["ready", "--run", str(run_dir), "--claim"], env=env, capture_output=True,
                                              text=True).stdout)
            for step in ready["ready"]:
                launch(step)
            if ready["complete"]:
                break
            time.sleep(0.02)
        for thread in workers:
            thread.join()
        verify = subprocess.run(kit + ["verify", "--run", str(run_dir)], env=env, capture_output=True, text=True)
        plan = json.loads((run_dir / "plan.json").read_text())
        run = dagkit.Run(run_dir)
        m = score.ledger_measures(plan, run.events(), run)
    for name, got, want in (("premature run refused (exit 3)", premature.returncode, 3), ("verify exit", verify.returncode, 0),
                            ("verify verdict", m["verify"], "OK"), ("refused events", m["refused"], 1),
                            ("peak concurrency >= 3", m["peak_concurrency"] >= 3, True), ("steps started twice", m["steps_started_twice"], 0),
                            ("time scale recorded", m["time_scale"], [0.05]), ("refill (completion-driven loop)", m["refill"], True)):
        cells += 1
        bad = got != want
        off += bad
        lines.append(f"{'OFF' if bad else 'ok ':<3} {'kit end to end':<42} {name:<32} want {want!r:<8} got {got!r}")
    return cells, off, lines


def _cell(lines: list, group: str, name: str, fn, want) -> tuple[int, int]:
    """One qualification cell: an exception is a failed cell, not a crash of the calibration."""
    try:
        got = fn()
    except Exception as error:  # noqa: BLE001
        got = f"ERROR {type(error).__name__}: {str(error)[:60]}"
    bad = got != want
    lines.append(f"{'OFF' if bad else 'ok ':<3} {group:<26} {name:<46} want {want!r:<22} got {got!r}")
    return 1, int(bad)


def _view(host: str, events: list) -> list:
    return [item for n, ev in enumerate(events, 1) for item in score.normalize(host, {"recv": float(n), "ev": ev})]


def _claude_call(name: str, command: str, owner=None, uid: str = "toolu_x") -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name,
                                                          "input": {"command": command, "description": command}}]},
            "parent_tool_use_id": owner}


def qualification_cells() -> tuple[int, int, list]:
    """Negative controls and contracts the owner's review asked for (README Amendments A2 to A4): each is a way the scorer,
    the kit or the launcher could credit an invalid trial. Written to fail first against the unfixed code."""
    lines: list = []
    cells = off = 0

    def cell(group, name, fn, want):
        nonlocal cells, off
        c, o = _cell(lines, group, name, fn, want)
        cells, off = cells + c, off + o
    kit = "python3 /tmp/x/work/dagkit.py"

    # ---- scorer: mechanism, report, tokens
    unrelated = _view("claude", [_claude_call("Agent", "unrelated", uid="toolu_a"),
                                 _claude_call("Bash", f"{kit} run --run r --step S1", uid="toolu_b"),
                                 _claude_call("Bash", f"{kit} run --run r --step S2", uid="toolu_c")])
    cell("scorer: mechanism", "unrelated spawn, parent runs the steps", lambda: score.mechanism(unrelated, {"peak_concurrency": 2}, True)["kind"],
         "parent-executed")
    kids = _view("claude", [_claude_call("Agent", "run S1", uid="toolu_a"), _claude_call("Agent", "run S2", uid="toolu_b"),
                            _claude_call("Bash", f"{kit} run --run r --step S1", owner="toolu_a", uid="toolu_c"),
                            _claude_call("Bash", f"{kit} run --run r --step S2", owner="toolu_b", uid="toolu_d")])
    cell("scorer: mechanism", "positive control: children ran the steps", lambda: score.mechanism(kids, {"peak_concurrency": 2}, True)["kind"], "native-agents")
    mixed = _view("claude", [_claude_call("Agent", "run S1", uid="toolu_a"),
                             _claude_call("Bash", f"{kit} run --run r --step S1", owner="toolu_a", uid="toolu_c"),
                             _claude_call("Bash", f"{kit} run --run r --step S2", uid="toolu_d")])
    cell("scorer: mechanism", "a child and the parent each ran a step", lambda: score.mechanism(mixed, {"peak_concurrency": 2}, True)["kind"], "mixed")
    cell("scorer: mechanism", "spawns on a host that cannot attribute calls", lambda: score.mechanism(unrelated, {"peak_concurrency": 2}, False)["kind"],
         "native-agents-unattributed")
    child = _view("claude", [{"type": "assistant", "message": {"content": [{"type": "text", "text": 'FINAL {"done":["S1"],"failed":[],"not_run":[]}'}]},
                             "parent_tool_use_id": "toolu_child"}])
    cell("scorer: report", "a child's FINAL is not the parent's report", lambda: score.final_claim(child), None)
    states = {"states": {"S1": "done", "S2": "running"}}
    cell("scorer: report", "a report omitting a running step", lambda: score.fidelity(states, {"done": ["S1"], "failed": [], "not_run": []})["fidelity_ok"], False)
    cell("scorer: report", "a report naming every step once, all done", lambda: score.fidelity({"states": {"S1": "done", "S2": "done"}},
         {"done": ["S1", "S2"], "failed": [], "not_run": []})["fidelity_ok"], True)
    pathname = _view("claude", [_claude_call("Bash", "python3 /tmp/parallel-probe/dagkit.py run --run r --step S1")])
    cell("scorer: mechanism", "a path that contains the word parallel", lambda: score.mechanism(pathname, {"peak_concurrency": 1}, True)["kind"], "parent-executed")
    long_cmd = f"cd /private/tmp/claude-501/some/very/long/scratchpad/path/ppe-trials/one-trial/work && {kit} run --run r --step S1 > /dev/null 2>&1 &"
    longview = _view("claude", [_claude_call("Bash", long_cmd)])
    cell("scorer: mechanism", "a background operator past column 140", lambda: score.mechanism(longview, {"peak_concurrency": 2}, True)["kind"], "shell-parallel")
    longrun = _view("claude", [_claude_call("Bash", "cd /private/tmp/claude-501/some/very/long/scratchpad/path/ppe-trials/one-trial/work/subdir/deeper && /usr/bin/python3 /private/tmp/claude-501/some/very/long/scratchpad/path/ppe-trials/one-trial/work/dagkit.py run --run r --step S1")])
    cell("scorer: mechanism", "a run call whose ' run ' is past column 140", lambda: score.mechanism(longrun, {"peak_concurrency": 1}, True)["kind"], "parent-executed")
    cell("scorer: tokens", "codex cached_input_tokens is the cache read", lambda: score.tokens(_view("codex", [
        {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 90, "output_tokens": 5}}]), "codex")["cache_read"], 90)
    # One result event per parent turn (README Amendment A7): in -p mode a background sub-agent's completion re-enters the parent as a new turn,
    # each result's usage covers its own turn only, and modelUsage is cumulative. The numbers below are the real r1h-claude-a3 stream's.
    shared = {"m": {"inputTokens": 60, "cacheReadInputTokens": 868158, "cacheCreationInputTokens": 64187, "outputTokens": 8474}}
    turns = [{"type": "result", "result": text, "total_cost_usd": 0.36, "modelUsage": shared, "usage": {
        "input_tokens": a, "cache_read_input_tokens": b, "cache_creation_input_tokens": c, "output_tokens": d}}
        for text, a, b, c, d in (("one", 6, 92370, 13295, 1623), ("two", 8, 159653, 5900, 917), ("three", 6, 132018, 1616, 455))]
    cell("scorer: tokens", "a Claude run with one result event per parent turn sums the parent's usage over every turn", lambda: (
        score.tokens(_view("claude", turns), "claude")["parent_input_all"], score.tokens(_view("claude", turns), "claude")["children_input_all"],
        score.tokens(_view("claude", turns), "claude")["output"]), (404872, 527533, 2995))
    cell("scorer: tokens", "a Claude run with a single result event is unchanged", lambda: (score.tokens(_view("claude", turns[2:]), "claude")["parent_input_all"]), 133640)
    # Grok's end usage covers the parent and every sub-agent session (the per-call log of r1-grok-a3: 659,155 = parent 185,909 + five children 473,246)
    gview = _view("grok", [{"type": "end", "usage": {"input_tokens": 100, "cache_read_input_tokens": 50, "output_tokens": 5}}])
    cell("scorer: tokens", "grok with sub-agents: the end usage is the whole run, the parent's share is not separable from the stream", lambda: (
        lambda g: (g["input_all"], g["parent_input_all"], g["children_included"]))(score.tokens(gview, "grok", {"agents": [{"actor": "agent:a"}]})), (150, None, True))
    cell("scorer: tokens", "grok with no sub-agents: the end usage is the parent's", lambda: (
        lambda g: (g["input_all"], g["parent_input_all"], g["children_included"]))(score.tokens(gview, "grok", {"agents": []})), (150, 150, None))
    cell("scorer: tools", "grok spawn_subagent is a spawn", lambda: [i["kind"] for i in _view("grok", [
        {"type": "tool_call", "toolCallId": "g1", "toolName": "spawn_subagent", "rawInput": {"prompt": "x"}}])], ["spawn"])
    cell("scorer: tools", "grok collect and stop are not spawns", lambda: [i["kind"] for i in _view("grok", [
        {"type": "tool_call", "toolCallId": "g2", "toolName": "get_command_or_subagent_output", "rawInput": {}},
        {"type": "tool_call", "toolCallId": "g3", "toolName": "kill_command_or_subagent", "rawInput": {}}])], ["wait", "call"])
    cell("scorer: tools", "claude TaskOutput is not a spawn", lambda: [i["kind"] for i in _view("claude", [_claude_call("TaskOutput", "t")])], ["call"])
    # ---- scorer: tails, comparison identity, validity
    tail_view = [{"t": 41.0, "actor": "parent", "kind": "final", "name": "", "text": "FINAL {}"},
                 {"t": 99.0, "actor": "parent", "kind": "text", "name": "", "text": "late chatter"}]
    cell("scorer: tails", "process tail is read from the last work event", lambda: {k: round(v, 1) for k, v in score.tails(
        tail_view, [{"ts": 10.0, "kind": "start", "step": "S1", "detail": {}}, {"ts": 40.0, "kind": "end", "step": "S1", "detail": {}}], 100.0).items()
        if k in ("tail_from_last_end_s", "tail_from_final_report_s")}, {"tail_from_last_end_s": 60.0, "tail_from_final_report_s": 59.0})
    rows = [{"path": "a0v1", "identity": {"host": "codex", "version": "1", "model": "m", "effort": "e", "plan": "fan4", "arm": "A0", "variant": "N", "enabled_features": []},
             "makespan_s": 120.0, "critical_path_declared_s": 30, "valid": True},
            {"path": "a0v2", "identity": {"host": "codex", "version": "1", "model": "m", "effort": "e", "plan": "fan4", "arm": "A0", "variant": "N", "enabled_features": ["multi_agent_v2"]},
             "makespan_s": 100.0, "critical_path_declared_s": 30, "valid": True},
            {"path": "a3v1", "identity": {"host": "codex", "version": "1", "model": "m", "effort": "e", "plan": "fan4", "arm": "A3", "variant": "N", "enabled_features": []},
             "makespan_s": 60.0, "critical_path_declared_s": 30, "valid": True},
            {"path": "a3bad", "identity": {"host": "codex", "version": "1", "model": "m", "effort": "e", "plan": "fan4", "arm": "A3", "variant": "H", "enabled_features": []},
             "makespan_s": 30.0, "critical_path_declared_s": 30, "valid": False}]
    cell("scorer: comparison", "an A3 trial is compared with its own profile's A0",
         lambda: {r["path"]: r.get("vs_A0") for r in score.compare_rows(rows)}.get("a3v1"), 0.5)
    cell("scorer: comparison", "an invalid trial earns no saving",
         lambda: {r["path"]: r.get("realized") for r in score.compare_rows(rows)}.get("a3bad"), None)
    # ---- kit contract
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        env = dict(os.environ, PPE_TIME_SCALE="0.02")
        k = [sys.executable, str(HERE / "dagkit.py")]

        def sh(*args):
            return subprocess.run(k + list(args), env=env, capture_output=True, text=True)
        fan, run = HERE / "plans" / "fan4.json", str(Path(root) / "fan")
        sh("init", "--plan", str(fan), "--run", run)
        first = json.loads(sh("ready", "--run", run, "--claim", "--capacity", "2").stdout or "{}")
        cell("kit: capacity", "claim at most the capacity", lambda: first.get("ready"), ["S1", "S2"])
        second = json.loads(sh("ready", "--run", run, "--claim", "--capacity", "2").stdout or "{}")
        cell("kit: capacity", "no claim while capacity is full", lambda: (second.get("ready"), second.get("deferred")), ([], ["S3", "S4"]))
        sh("release", "--run", run, "--step", "S2")
        third = json.loads(sh("ready", "--run", run, "--claim", "--capacity", "2").stdout or "{}")
        cell("kit: release", "a released claim is offered again", lambda: third.get("ready"), ["S2"])
        sh("run", "--run", run, "--step", "S1")
        events = dagkit.Run(run).events()
        cell("kit: claims", "claims never followed by a start are counted", lambda: score.ledger_measures(json.loads(fan.read_text()), events)["claims_without_start"], 1)
        # refusal categories and the verdict contract on the ragged plan
        rag, run2 = HERE / "plans" / "ragged6.json", str(Path(root) / "rag")
        sh("init", "--plan", str(rag), "--run", run2)
        sh("run", "--run", run2, "--step", "S4")
        sh("run", "--run", run2, "--step", "S9")
        sh("run", "--run", run2, "--step", "S1")
        sh("run", "--run", run2, "--step", "S1")
        cats = [e["detail"].get("category") for e in dagkit.Run(run2).events() if e["kind"] == "refused"]
        cell("kit: refusals", "premature, unknown and duplicate are told apart", lambda: cats, ["premature", "unknown", "duplicate"])
        # tamper: a second terminal event, then an altered plan
        led = Path(run2) / "ledger.jsonl"
        lines0 = led.read_text().splitlines()
        end1 = [json.loads(x) for x in lines0 if json.loads(x)["kind"] == "end"][0]
        dup = dict(end1, seq=len(lines0) + 1)
        led.write_text("\n".join(lines0 + [json.dumps(dup)]) + "\n")
        cell("kit: verify", "a second terminal event is a FAIL", lambda: dagkit.verdict(dagkit.Run(run2))[0], "FAIL")
        led.write_text("\n".join(lines0) + "\n")
        plan_path = Path(run2) / "plan.json"
        original = plan_path.read_text()
        plan_path.write_text(original.replace('"seconds": 40', '"seconds": 41'))
        cell("kit: verify", "a plan changed after init is a FAIL", lambda: dagkit.verdict(dagkit.Run(run2))[0], "FAIL")
        plan_path.write_text(original)
        (Path(run2) / "out" / "S1.json").write_text(json.dumps({"step": "S1", "inputs": {}, "sha": "0" * 64}))
        sh("run", "--run", run2, "--step", "S2")
        sh("run", "--run", run2, "--step", "S3")
        late = sh("run", "--run", run2, "--step", "S4")
        cell("kit: inputs", "a step refuses a predecessor output that does not match the ledger", lambda: late.returncode, 3)
        scaled_events = [e for e in dagkit.Run(run2).events()]
        cell("scorer: validity", "a scaled run is flagged", lambda: score.ledger_measures(json.loads(rag.read_text()), scaled_events)["scaled_trial"], True)
    # ---- the real launcher path with no model call
    sys.path.insert(0, str(HERE))
    import launch
    with tempfile.TemporaryDirectory() as root:
        for host in ("claude", "codex", "grok"):
            out = Path(root) / f"t-{host}"

            def run_launch():
                import io
                import contextlib
                with contextlib.redirect_stdout(io.StringIO()):
                    launch.main(["--host", host, "--plan", "one1", "--arm", "A0", "--binary", str(HERE / "fakehost.py"), "--out", str(out), "--timeout", "60"])
                m = json.loads((out / "score.json").read_text())
                return (m.get("verify"), m["mechanism"]["kind"], m.get("fidelity_ok"), (out / "invocation.json").is_file())
            cell("launcher: normal path", f"{host} through the real adapter and the fake host", run_launch, ("OK", "parent-executed", True, True))
    return cells, off, lines


def task_cells() -> tuple[int, int, list]:
    """Real-agent-work mode (README Amendment A5): the kit's begin, complete and outcome, the evidence oracle, the readers on the
    real E1 streams when PPE_E1_DIR names them, the FINAL line in pieces, and the launcher's task path with a fake host."""
    import tempfile
    import evidence
    lines: list = []
    cells = off = 0

    def cell(group, name, fn, want):
        nonlocal cells, off
        c, o = _cell(lines, group, name, fn, want)
        cells, off = cells + c, off + o
    k = [sys.executable, str(HERE / "dagkit.py")]
    with tempfile.TemporaryDirectory() as root:
        env = dict(os.environ)

        def sh(*args):
            return subprocess.run(k + list(args), env=env, capture_output=True, text=True)
        run = str(Path(root) / "work" / "run")
        (Path(root) / "work").mkdir()
        sh("init", "--plan", str(HERE / "plans" / "analysis5.json"), "--run", run)
        premature = sh("begin", "--run", run, "--step", "T5")
        cell("kit: task mode", "a dependent task is refused before its inputs", lambda: premature.returncode, 3)
        wrong = sh("run", "--run", run, "--step", "T1")
        cell("kit: task mode", "run is refused on a task step", lambda: wrong.returncode, 3)
        nostart = sh("complete", "--run", run, "--step", "T1", "--result", '{"answer": 1}')
        cell("kit: task mode", "complete before begin is refused", lambda: nostart.returncode, 3)
        begun = sh("begin", "--run", run, "--step", "T1")
        cell("kit: task mode", "begin prints the task and the exact callback", lambda: ("complete --run" in begun.stdout and "log_1.txt" in begun.stdout and begun.returncode == 0), True)
        bad = sh("complete", "--run", run, "--step", "T1", "--result", '{"answer": "five"}')
        cell("kit: task mode", "a result with no integer answer is refused", lambda: bad.returncode, 3)
        good = sh("complete", "--run", run, "--step", "T1", "--result", '{"answer": 5, "method": "x"}')
        cell("kit: task mode", "complete records the outcome", lambda: (good.returncode, "RECORDED T1" in good.stdout), (0, True))
        again = sh("begin", "--run", run, "--step", "T1")
        cell("kit: task mode", "a second begin is a duplicate", lambda: again.returncode, 3)
        out1 = sh("outcome", "--run", run, "--step", "T1")
        cell("kit: task mode", "outcome prints a finished step's result", lambda: json.loads(out1.stdout)["result"]["answer"], 5)
        out2 = sh("outcome", "--run", run, "--step", "T2")
        cell("kit: task mode", "outcome refuses an unfinished step", lambda: out2.returncode, 3)
        for step, answer in (("T2", 7), ("T3", 3), ("T4", 100)):
            sh("begin", "--run", run, "--step", step)
            sh("complete", "--run", run, "--step", step, "--result", json.dumps({"answer": answer}))
        sh("begin", "--run", run, "--step", "T5")
        sh("complete", "--run", run, "--step", "T5", "--result", '{"answer": 115}')
        cell("kit: task mode", "a finished task plan verifies OK", lambda: dagkit.verdict(dagkit.Run(run))[0], "OK")
        cats = [e["detail"].get("category") for e in dagkit.Run(run).events() if e["kind"] == "refused"]
        cell("kit: task mode", "refusal categories", lambda: cats, ["premature", "wrong-command", "not-started", "bad-result", "duplicate", "premature"])
        tamper = Path(run) / "out" / "T2.json"
        record = json.loads(tamper.read_text())
        record["result"]["answer"] = 8
        tamper.write_text(json.dumps(record))
        cell("kit: task mode", "an outcome edited after it was recorded breaks the chain", lambda: dagkit.verdict(dagkit.Run(run))[0], "FAIL")
    # the settle dial: a slow verification inside every task (the work-length dial of the scaling trials); `complete` insists on it
    with tempfile.TemporaryDirectory() as root:
        senv = dict(os.environ, PPE_TIME_SCALE="0.01")

        def ssh(*args):
            return subprocess.run(k + list(args), env=senv, capture_output=True, text=True)
        srun = str(Path(root) / "swork" / "run")
        (Path(root) / "swork").mkdir()
        ssh("init", "--plan", str(HERE / "plans" / "analysis5.json"), "--run", srun, "--settle", "40")
        early = ssh("settle", "--run", srun, "--step", "T1")
        cell("kit: settle dial", "settle before begin is refused", lambda: early.returncode, 3)
        sbegun = ssh("begin", "--run", srun, "--step", "T1")
        cell("kit: settle dial", "begin tells the agent to run the settle command and how long it takes", lambda: ("settle --run" in sbegun.stdout and "40 seconds" in sbegun.stdout), True)
        cell("kit: settle dial", "a run with no settle never mentions one", lambda: "settle --run" in begun.stdout, False)
        skipped = ssh("complete", "--run", srun, "--step", "T1", "--result", '{"answer": 5}')
        cell("kit: settle dial", "complete is refused until the settle has finished", lambda: (skipped.returncode, "not-settled" in "".join(
            e["detail"].get("category", "") for e in dagkit.Run(srun).events() if e["kind"] == "refused")), (3, True))
        began = time.time()
        settled = ssh("settle", "--run", srun, "--step", "T1")
        cell("kit: settle dial", "settle runs for the declared time (scaled) and says so", lambda: (settled.returncode, "SETTLED T1" in settled.stdout, 0.3 <= time.time() - began < 6), (0, True, True))
        again2 = ssh("settle", "--run", srun, "--step", "T1")
        cell("kit: settle dial", "a second settle is a duplicate", lambda: again2.returncode, 3)
        finished = ssh("complete", "--run", srun, "--step", "T1", "--result", '{"answer": 5}')
        cell("kit: settle dial", "complete succeeds after the settle", lambda: finished.returncode, 0)
        late = ssh("settle", "--run", srun, "--step", "T1")
        cell("kit: settle dial", "settle after the outcome is refused", lambda: late.returncode, 3)
        for step, answer in (("T2", 7), ("T3", 3), ("T4", 100), ("T5", 115)):
            for call in (("begin",), ("settle",), ("complete", "--result", json.dumps({"answer": answer}))):
                ssh(call[0], "--run", srun, "--step", step, *call[1:])
        srunner = dagkit.Run(srun)
        splan = srunner.plan()
        cell("kit: settle dial", "a finished settled plan verifies OK with every step settled", lambda: (
            dagkit.verdict(srunner)[0], score.ledger_measures(splan, srunner.events())["settled_all"]), ("OK", True))
        hand = [e for e in srunner.events() if not (e["kind"] == "settled" and e["step"] == "T2")]
        cell("scorer: settle", "a step that ended with no settle is detected (a hand-made ledger: the kit cannot make one)", lambda: score.ledger_measures(splan, hand)["settled_all"], False)
        nosettle = [dict(e, detail=dict(e["detail"], settle=0.0)) if e["kind"] == "init" else e for e in hand]
        cell("scorer: settle", "a run declared with no settle leaves the check unset even when a step has none", lambda: score.ledger_measures(splan, nosettle)["settled_all"], None)
    files_a, expected_a = evidence.generate(11, 150)
    files_b, expected_b = evidence.generate(11, 150)
    cell("evidence", "the same seed gives the same logs and answers", lambda: files_a == files_b and expected_a == expected_b, True)
    cell("evidence", "the final answer is the sum of the four", lambda: expected_a["T5"] == sum(expected_a[f"T{n}"] for n in range(1, 5)), True)
    cell("evidence", "the oracle's sliding-window reader equals the brute-force one", lambda: all(
        evidence.q1(evidence.generate(s, 120)[0]["log_1.txt"]) == evidence.q1_brute(evidence.generate(s, 120)[0]["log_1.txt"]) for s in range(1, 9)), True)
    # the FINAL line streamed in pieces, and an answer scored against the oracle
    pieces = _view("grok", [{"type": "text", "data": "done\nFIN"}, {"type": "text", "data": 'AL {"done":["T1"],"failed":[],"not_run":[],"answer":9}'}])
    cell("scorer: report", "a FINAL line split across text deltas is read", lambda: score.final_claim(pieces), {"done": ["T1"], "failed": [], "not_run": [], "answer": 9})
    with tempfile.TemporaryDirectory() as root:
        trial = Path(root)
        (trial / "work" / "run" / "out").mkdir(parents=True)
        (trial / "oracle.json").write_text(json.dumps({"T1": 5, "T2": 7, "T3": 3, "T4": 100, "T5": 115}))
        plan = json.loads((HERE / "plans" / "analysis5.json").read_text())
        for step, answer in (("T1", 5), ("T2", 7), ("T3", 4), ("T5", 115)):
            (trial / "work" / "run" / "out" / f"{step}.json").write_text(json.dumps({"result": {"answer": answer}}))
        scored = score.answers(trial, plan)
        cell("scorer: answers", "three right, one wrong, one never recorded", lambda: (scored["correct"], scored["tasks"]["T3"]["correct"], scored["tasks"]["T4"]["recorded"]), (3, False, None))
    # the readers on the real E1 streams, when they are on this machine
    e1 = os.environ.get("PPE_E1_DIR")
    if e1 and (Path(e1) / "e1-claude").is_dir():
        for host in ("claude", "codex", "grok"):
            trial = Path(e1) / f"e1-{host}"
            cell(f"readers on real E1: {host}", "one native sub-agent, its command attributed to it", lambda: (
                len(score.native_agents(trial, host)["agents"]),
                score.mechanism(score.host_view(trial, host), {"peak_concurrency": 1}, True)["kind"]), (1, "native-agents"))
        cell("readers on real E1: grok", "the FINAL line is found in the streamed text", lambda: score.final_claim(score.host_view(Path(e1) / "e1-grok", "grok")), {"done": ["S1"], "failed": [], "not_run": []})
        cell("readers on real E1: codex", "the child thread records its multi-agent version", lambda: score.codex_threads(Path(e1) / "e1-codex")[-1]["version"] in ("v1", "v2"), True)
    # the parent's model calls on real pilot and E11 trials (README Amendment A8): how many spawn calls each model call issued
    if e1 and all((Path(e1) / n).is_dir() for n in ("r1h-claude-a3", "r1-grok-a3", "e11-grok-h1", "r1-codex-a3")):
        import context
        for name, want in (("r1h-claude-a3", [4, 1]), ("r1-grok-a3", [4, 1]), ("e11-grok-h1", [4, 1]), ("r1-codex-a3", [1, 1, 1, 1, 1])):
            cell("readers on real trials: model calls", f"{name}: spawn calls issued per parent model call", lambda: [
                n for n in (len([x for x in turn["tools"] if "spawn" in str(x).lower() or x in ("Agent", "Task")]) for turn in context.read_trial(Path(e1) / name)["parent_turns"]) if n], want)
    # the launcher's task path through the real adapters and the fake host
    sys.path.insert(0, str(HERE))
    import launch
    with tempfile.TemporaryDirectory() as root:
        for host in ("claude", "codex", "grok"):
            out = Path(root) / f"task-{host}"

            def run_launch():
                import io
                import contextlib
                with contextlib.redirect_stdout(io.StringIO()):
                    launch.main(["--host", host, "--plan", "analysis5", "--arm", "A0", "--binary", str(HERE / "fakehost.py"), "--out", str(out), "--timeout", "60", "--lines", "80"])
                m = json.loads((out / "score.json").read_text())
                return (m.get("verify"), m["answers"]["correct"], m.get("final_answer_ok"), m["mechanism"]["kind"], (out / "oracle.json").is_file(), (out / "work" / "evidence" / "log_1.txt").is_file())
            cell("launcher: task path", f"{host}: evidence, oracle, answers and report", run_launch, ("OK", 5, True, "parent-executed", True, True))
        out = Path(root) / "task-settle"

        def run_settle_launch():
            import io
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                launch.main(["--host", "grok", "--plan", "analysis5", "--arm", "A0", "--binary", str(HERE / "fakehost.py"), "--out", str(out), "--timeout", "60",
                             "--lines", "80", "--settle", "30"])
            m = json.loads((out / "score.json").read_text())
            inv = json.loads((out / "invocation.json").read_text())
            return (m.get("verify"), m["answers"]["correct"], m.get("settled_all"), m.get("settle_s"), inv.get("settle_s"))
        cell("launcher: task path", "a settle is passed to the kit, recorded in the invocation and seen by the scorer", run_settle_launch, ("OK", 5, True, 30.0, 30.0))
    return cells, off, lines


def identity_cells() -> tuple[int, int, list]:
    """The identity probe (README Amendment A7): whoami.py under made-up environments, and the judge on canned reports."""
    import tempfile
    sys.path.insert(0, str(HERE))
    import identity
    lines: list = []
    cells = off = 0

    def cell(group, name, fn, want):
        nonlocal cells, off
        c, o = _cell(lines, group, name, fn, want)
        cells, off = cells + c, off + o
    with tempfile.TemporaryDirectory() as root:
        script = identity.make_whoami(Path(root) / "whoami.py")

        def who(extra: dict) -> dict:
            env = {"PATH": os.environ["PATH"], **extra}   # never the calibrating session's own environment
            done = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
            return json.loads(done.stdout)
        cell("identity: whoami", "a Codex thread id means codex, and only its last six characters are kept",
             lambda: (lambda r: (r["detect_host"], r["ids"]))(who({"CODEX_THREAD_ID": "019aaaaaabcdef"})), ("codex", {"CODEX_THREAD_ID": "abcdef"}))
        cell("identity: whoami", "a Grok session id means grok", lambda: who({"GROK_SESSION_ID": "sess-123456"})["detect_host"], "grok")
        cell("identity: whoami", "CLAUDECODE means claude", lambda: who({"CLAUDECODE": "1"})["detect_host"], "claude")
        cell("identity: whoami", "no marker is unknown, with no markers listed", lambda: (lambda r: (r["detect_host"], r["markers"]))(who({})), ("unknown", []))
        cell("identity: whoami", "a nested host wins over its launcher (innermost first)", lambda: who({"CLAUDECODE": "1", "CODEX_THREAD_ID": "x1"})["detect_host"], "codex")
        cell("identity: whoami", "marker names are listed, values are not", lambda: (lambda r: ("CODEX_SANDBOX" in r["markers"], "seatbelt" in json.dumps(r)))(
            who({"CODEX_SANDBOX": "seatbelt"})), (True, False))
    parent = {"detect_host": "grok", "markers": ["GROK_AGENT"], "ids": {"GROK_SESSION_ID": "aaaaaa"}, "ancestors": ["grok"]}
    child = {"detect_host": "grok", "markers": ["GROK_AGENT"], "ids": {"GROK_SESSION_ID": "bbbbbb"}, "ancestors": ["grok"]}
    ok = identity.judge("grok", {"parent": parent, "child": child, "parent_tools": ["spawn_subagent", "run_terminal_command"], "child_tools": ["run_terminal_command"]}, 1)
    cell("identity: judge", "both contexts right, ids differ, markers equal, the child cannot spawn", lambda: (
        ok["parent_right"], ok["child_right"], ok["ids_differ"], ok["markers_same"], ok["child_can_spawn"], ok["native_agents"]), (True, True, True, True, False, 1))
    wrong = identity.judge("grok", {"parent": parent, "child": dict(child, detect_host="unknown", markers=[]), "child_tools": ["spawn_subagent"]}, 1)
    cell("identity: judge", "a sub-agent that detects unknown is flagged, with differing markers", lambda: (wrong["child_right"], wrong["markers_same"], wrong["child_can_spawn"]), (False, False, True))
    none = identity.judge("claude", None, 0)
    cell("identity: judge", "no FINAL line is a failed probe, not a pass", lambda: (none["reported"], none["parent_right"], none["child_ran"], none["child_can_spawn"]), (False, False, False, None))
    cell("identity: judge", "the Agent tool counts as a spawn tool", lambda: identity.judge("claude", {"parent": parent, "child": child, "child_tools": ["Agent"]}, 1)["child_can_spawn"], True)
    return cells, off, lines


def main() -> int:
    total = bad = 0
    for part in (check(CASES), view_cells(), kit_end_to_end(), qualification_cells(), task_cells(), identity_cells()):
        n, off, lines = part
        print("\n".join(lines))
        total, bad = total + n, bad + off
    print(f"cells: {total}, off: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
