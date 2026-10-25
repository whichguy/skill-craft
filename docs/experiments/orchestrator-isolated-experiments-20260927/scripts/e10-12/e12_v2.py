"""E12/X11/X12 adapted to e707b794.

Same pure-API traversal as e12_head_size.walk (nav.new_state/apply/finish_improve), but it measures what `next`
actually prints (nav.printed_text: whole up to PRINT_LIMIT, else a head for an active run or a pointer otherwise) as
well as nav.packet_head, and whether an implement print names its step.  The internal `sections` breakdown is dropped
(those helpers changed signature).  The add-ons' paused/halted/blocked probes follow; blocked now needs `awaiting`.
"""
import re, statistics, sys, tempfile
from pathlib import Path
import e12_head_size as e
nav = e.nav
STEP = re.compile(r"^Step S\d+ \(\d+ of \d+\)", re.M)


SRC = str(e.HERE.parent / "src")
def ref_len(run):
    """Length at the reference install (test/shiploop_head_budget.py: run dir 83, package root 63 chars)."""
    work = str(run.parent)
    return lambda t: len(t) + t.count(work) * (83 - len("/.shiploop") - len(work)) + t.count(SRC) * (63 - len(SRC))

def measure(run, state):
    path = nav.packet_path(run, state)
    full = nav.render(e.CORE, run, state)
    m = ref_len(run)
    printed = nav.printed_text(e.CORE, run, state, path, full, measure=m)
    head = nav.packet_head(e.CORE, run, state, path, measure=m) if state["status"] == "active" else ""
    full, printed, head = (type("L", (str,), {"__len__": lambda self, m=m: m(str(self))})(x) for x in (full, printed, head))
    kind = "whole" if printed == full + nav.HEAD_END + "\n" else ("pointer" if printed.startswith("Full packet: ") else "head")
    return full, printed, head, kind


def walk(n, heavy, stop=None):
    root = Path(tempfile.mkdtemp(prefix=f"e12v2-n{n}-{'h' if heavy else 'l'}-", dir=e.HERE / "e12-work"))
    run = root / ".shiploop"; run.mkdir()
    state = nav.new_state(str(root / "repo"), "E12 head-size probe: " + (e.long(2000) if heavy else "x"),
                          improve_skill="", lint_option="off")
    rows, c = [], {}
    while state["status"] == "active":
        if stop and stop(state):
            return run, state, rows
        full, printed, head, kind = measure(run, state)
        stage = nav.current_stage(state) + (" (improve)" if state.get("active_improve") else "")
        rows.append({"stage": stage, "full": len(full), "printed": len(printed), "head": len(head), "kind": kind,
                     "step_in_printed": bool(STEP.search(printed)), "step_in_head": bool(STEP.search(head))})
        a = nav.current_action(state)["id"]
        state = (nav.finish_improve(state, a, {"summary": "S " + (e.long(1500) if heavy else ""), "review_refs": ["s://r"],
                                               "check_refs": ["s://c"], "lessons": "x"})
                 if state.get("active_improve") else nav.apply(state, a, e.results_for(nav.current_stage(state), n, heavy, c)))
    return run, state, rows


def main():
    (e.HERE / "e12-work").mkdir(exist_ok=True)
    print("PRINT_LIMIT", nav.PRINT_LIMIT, "HEAD_LIMIT", nav.HEAD_LIMIT)
    for heavy in (False, True):
        for n in ([1, 10, 30] if "--quick" not in sys.argv else [1, 10]):
            run, state, rows = walk(n, heavy)
            impl = [r for r in rows if r["stage"] == "implement"]
            kinds = {k: sum(r["kind"] == k for r in rows) for k in ("whole", "head", "pointer")}
            print(f"n={n} {'heavy' if heavy else 'light'}: packets={len(rows)} printed max={max(r['printed'] for r in rows)} "
                  f"mean={round(statistics.mean(r['printed'] for r in rows))} head max={max(r['head'] for r in rows)} "
                  f"full max={max(r['full'] for r in rows)} kinds={kinds} | implement prints={len(impl)} "
                  f"naming step: printed {sum(r['step_in_printed'] for r in impl)}, head {sum(r['step_in_head'] for r in impl)}")
            full, printed, _, kind = measure(run, state)
            print(f"   done packet: full={len(full)} printed={len(printed)} kind={kind}")
    # add-on: non-active packets at W21 implement, heavy
    run, state, _ = walk(30, True, stop=lambda s: nav.current_stage(s) == "implement" and s["work_index"] == 20
                         and not s.get("active_improve"))
    _, printed, head, kind = measure(run, state)
    print(f"W21 implement active: printed={len(printed)} kind={kind} head={len(head)} step named in print: {bool(STEP.search(printed))}")
    for verb in ("pause", "halt"):
        s2 = nav.control(state, verb, "User asked: " + e.long(3000))
        full, printed, _, kind = measure(run, s2)
        print(f"{verb}: full={len(full)} printed={len(printed)} kind={kind}")
    s3 = nav.apply(state, nav.current_action(state)["id"],
                   {"outcome": "blocked", "summary": e.long(3000),
                    "awaiting": {"kind": "service", "service": "svc " + e.long(500), "check": "true",
                                 "no_default": "Nothing else can proceed."}})
    full, printed, _, kind = measure(run, s3)
    print(f"blocked: status={s3['status']} full={len(full)} printed={len(printed)} kind={kind}")


if __name__ == "__main__":
    main()
