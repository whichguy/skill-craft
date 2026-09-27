"""E12 add-on 2: what makes a whole-printed paused packet large? light vs heavy, early vs late."""
import tempfile
from pathlib import Path
import e12_head_size as e
nav = e.nav
def at(heavy, stop_item, stop_stage="implement"):
    root = Path(tempfile.mkdtemp(prefix="e12-addon2-", dir=e.HERE / "e12-work")); run = root / ".shiploop"; run.mkdir()
    state = nav.new_state(str(root / "repo"), "E12 add-on " + (e.long(2000) if heavy else "x"), improve_skill="", lint_option="off")
    c = {}
    while not (nav.current_stage(state) == stop_stage and (stop_item is None or state["work_index"] == stop_item)):
        a = nav.current_action(state)["id"]
        state = (nav.finish_improve(state, a, {"summary": "S " + (e.long(1500) if heavy else ""), "review_refs": ["s://r"], "check_refs": ["s://c"], "lessons": "x"})
                 if state.get("active_improve") else nav.apply(state, a, e.results_for(nav.current_stage(state), 30, heavy, c)))
    return run, state
for heavy in (False, True):
    for item in (0, 20):
        run, st = at(heavy, item)
        p = nav.render(e.CORE, run, nav.control(st, "pause", "User asked to pause."))
        print(f"{'heavy' if heavy else 'light'} W{item+1} implement paused packet: {len(p.encode())} bytes")
        if heavy and item == 20:
            open("e12_paused_packet_heavy_W21.txt", "w").write(p)
            # largest blocks between blank lines
            blocks = p.split("\n\n")
            for b in sorted(blocks, key=len, reverse=True)[:6]:
                print(f"   {len(b.encode()):>6}  {b.splitlines()[0][:110]!r}")
