"""E12: printed packet-head bytes (what `shiploop next` prints for an active run) at every stage.

Pure navigator API (new_state/apply/finish_improve/packet_head/render), the same traversal the
dry-run module uses, with deliberately heavy synthetic declarations.  A real run directory under
this experiment folder is used so every printed path has a realistic length.
"""
import json, os, statistics, sys, tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "src/skills/shiploop"
sys.path.insert(0, str(PKG / "scripts"))
os.environ.update(SHIPLOOP_KEEPALIVE="off", SHIPLOOP_KEEPALIVE_HOME=str(HERE / "keepalive-home"))
import shiploop_navigator as nav  # noqa: E402

CORE = SimpleNamespace(PACKAGE_ROOT=PKG, REF_DIR=PKG / "references")
LONG = ("This sentence is deliberately verbose so that any host-written text that the navigator copies "
        "into the printed head shows up as growth in the measured bytes. ")


def long(n):
    return (LONG * (n // len(LONG) + 1))[:n]


def results_for(stage, n_items, heavy, counter):
    counter[stage] = counter.get(stage, 0) + 1
    summary = (f"{stage} #{counter[stage]}: " + long(1500)) if heavy else "Synthetic declaration; no work executed."
    r = {"outcome": "done", "summary": summary}
    if stage == "plan":
        r["work_items"] = [{"id": f"W{i}", "title": f"W{i} " + long(150 if heavy else 20),
                            "context": long(800 if heavy else 20)} for i in range(1, n_items + 1)]
    if stage == "step-plan":
        crit = [{"id": f"C{i}", "text": long(300 if heavy else 20)} for i in range(1, (10 if heavy else 1) + 1)]
        cmds = []
        for i in range(1, (8 if heavy else 1) + 1):
            cmds.append({"command": f"python3 -m pytest tests/test_module_{i}.py -k '" + "and ".join(
                f"case_{j} " for j in range(12)) + "' --maxfail=1 -q" if heavy else "python3 -m unittest",
                "suite": "focused" if i <= 4 else "regression" if i <= 7 else "check",
                **({"criteria": [c["id"] for c in crit[3 * (i - 1):3 * i]]} if heavy and i <= 4 else {})})
        if not heavy:
            cmds[0]["criteria"] = ["C1"]
        r.update(paths=[f"src/module_{i}.py" for i in range(8)] + ["tests/**"], criteria=crit,
                 steps=[{"id": f"S{i}", "task": long(300 if heavy else 20)} for i in range(1, 6)],
                 test_commands=cmds)
    if stage == "system-test-author":
        r["system_commands"] = [{"command": "python3 -m pytest tests/system -q " + long(100 if heavy else 0).replace(" ", "_")[:100],
                                 "suite": "focused"}] * 1
    return r


def sections(root, state, path):
    stage = nav.current_stage(state); action = nav.current_action(state)
    parts = {
        "callback": "\n".join(nav._first_callback_lines(CORE, root, state)),
        "goal": "\n".join(nav._goal_lines(state, stage)),
        "result_contract": "\n".join(nav._result_contract_lines(root, state, stage, action["id"])
                                     if not state.get("active_improve") else []),
        "status_block": nav.status_block(state),
    }
    return {k: len(v.encode()) for k, v in parts.items()}


def walk(n_items, heavy, delivery=False):
    root = Path(tempfile.mkdtemp(prefix=f"e12-n{n_items}-{'heavy' if heavy else 'light'}-", dir=HERE / "e12-work"))
    run = root / ".shiploop"
    run.mkdir()
    state = nav.new_state(str(root / "repo"), "E12 head-size probe: " + (long(2000) if heavy else "x"),
                          improve_skill="", lint_option="off", delivery_contract=delivery)
    rows, counter = [], {}
    for _ in range(5000):
        if state["status"] != "active":
            break
        path = nav.packet_path(run, state)
        head = nav.packet_head(CORE, run, state, path)
        full = nav.render(CORE, run, state)
        stage = nav.current_stage(state)
        item = state["work_items"][state["work_index"]]["id"] if state.get("stage") == "inner-loop" else "root"
        rows.append({"stage": stage + (" (improve)" if state.get("active_improve") else ""), "item": item,
                     "head_bytes": len(head.encode()), "full_bytes": len(full.encode()),
                     "sections": sections(run, state, path)})
        action = nav.current_action(state)["id"]
        if state.get("active_improve"):
            state = nav.finish_improve(state, action, {"summary": "Synthetic Improve. " + (long(1500) if heavy else ""),
                                                       "review_refs": ["synthetic://r"], "check_refs": ["synthetic://c"],
                                                       "lessons": long(500) if heavy else "x"})
        else:
            state = nav.apply(state, action, results_for(stage, n_items, heavy, counter))
    assert state["status"] == "done", state["status"]
    return rows


def main():
    (HERE / "e12-work").mkdir(exist_ok=True)
    summary = {}
    for heavy in (False, True):
        for n in (1, 10, 30):
            rows = walk(n, heavy)
            key = f"n={n} {'heavy' if heavy else 'light'}"
            heads = [r["head_bytes"] for r in rows]
            top = max(rows, key=lambda r: r["head_bytes"])
            by_stage = {}
            for r in rows:
                by_stage.setdefault(r["stage"], []).append(r["head_bytes"])
            sec_max = {k: max(r["sections"][k] for r in rows) for k in rows[0]["sections"]}
            summary[key] = {"packets": len(rows), "head_max": max(heads), "head_mean": round(statistics.mean(heads)),
                            "head_min": min(heads), "max_at": f"{top['item']}:{top['stage']}",
                            "max_sections": top["sections"], "section_max_over_run": sec_max,
                            "full_max": max(r["full_bytes"] for r in rows),
                            "full_mean": round(statistics.mean(r["full_bytes"] for r in rows)),
                            "stage_max": {s: max(v) for s, v in by_stage.items()},
                            "first_item_vs_last_item_select_work": [r["head_bytes"] for r in rows if r["stage"] == "select-work"][:1]
                            + [r["head_bytes"] for r in rows if r["stage"] == "select-work"][-1:]}
            (HERE / f"e12_rows_{key.replace(' ', '_').replace('=', '')}.json").write_text(json.dumps(rows, indent=1))
            s = summary[key]
            print(f"{key:<12} packets={s['packets']:<5} head max={s['head_max']:<6} mean={s['head_mean']:<6} min={s['head_min']:<5} "
                  f"max@{s['max_at']:<22} full max={s['full_max']} mean={s['full_mean']}")
            print(f"             sections at max: {s['max_sections']}  | section max over run: {s['section_max_over_run']}")
            print(f"             select-work first/last item head: {s['first_item_vs_last_item_select_work']}")
    (HERE / "e12_summary.json").write_text(json.dumps(summary, indent=1))
    top_stages = sorted(summary["n=30 heavy"]["stage_max"].items(), key=lambda kv: -kv[1])[:8]
    print("n=30 heavy, largest heads by stage:", top_stages)


if __name__ == "__main__":
    main()
