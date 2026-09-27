"""E12 add-on: (1) whole-printed non-active packets (paused/blocked) mid-run with heavy data;
(2) delivery-contract run heads (template inlined up to 6000 chars) at the first stages."""
import tempfile
from pathlib import Path
import e12_head_size as e
nav = e.nav
root = Path(tempfile.mkdtemp(prefix="e12-addon-", dir=e.HERE / "e12-work")); run = root / ".shiploop"; run.mkdir()
state = nav.new_state(str(root / "repo"), "E12 add-on " + e.long(2000), improve_skill="", lint_option="off")
counter = {}
while not (nav.current_stage(state) == "implement" and state["work_index"] == 20):
    a = nav.current_action(state)["id"]
    state = (nav.finish_improve(state, a, {"summary": "S " + e.long(1500), "review_refs": ["s://r"], "check_refs": ["s://c"], "lessons": "x"})
             if state.get("active_improve") else nav.apply(state, a, e.results_for(nav.current_stage(state), 30, True, counter)))
for verb in ("pause", "halt"):
    s2 = nav.control(state, verb, "User asked: " + e.long(3000))
    print(f"{verb} packet (printed whole) at W21 implement: {len(nav.render(e.CORE, run, s2).encode())} bytes")
s3 = nav.apply(state, nav.current_action(state)["id"], {"outcome": "blocked", "blocked_by": "external", "summary": e.long(3000)})
print(f"blocked packet (printed whole) at W21 implement: {len(nav.render(e.CORE, run, s3).encode())} bytes")
print("active head at same point:", len(nav.packet_head(e.CORE, run, state, nav.packet_path(run, state)).encode()))
d = nav.new_state(str(root / "repo2"), "E12 delivery", improve_skill="", lint_option="off", delivery_contract=True)
for i in range(3):
    h = nav.packet_head(e.CORE, run, d, nav.packet_path(run, d))
    print(f"delivery-contract run {nav.current_stage(d)} head: {len(h.encode())} bytes")
    try:
        d = nav.apply(d, nav.current_action(d)["id"], {"outcome": "done", "summary": "x"})
    except Exception as exc:
        print("  (cannot advance delivery run with a plain result:", str(exc)[:120], ")"); break
