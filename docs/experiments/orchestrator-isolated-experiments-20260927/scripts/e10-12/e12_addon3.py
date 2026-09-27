"""E12 add-on 3: size of the whole-printed done packet after 1/10/30 heavy items."""
import tempfile
from pathlib import Path
import e12_head_size as e
nav = e.nav
for n in (1, 10, 30):
    root = Path(tempfile.mkdtemp(prefix="e12-done-", dir=e.HERE / "e12-work")); run = root / ".shiploop"; run.mkdir()
    s = nav.new_state(str(root / "repo"), "E12 done " + e.long(2000), improve_skill="", lint_option="off"); c = {}
    while s["status"] == "active":
        a = nav.current_action(s)["id"]
        s = (nav.finish_improve(s, a, {"summary": "S " + e.long(1500), "review_refs": ["s://r"], "check_refs": ["s://c"], "lessons": "x"})
             if s.get("active_improve") else nav.apply(s, a, e.results_for(nav.current_stage(s), n, True, c)))
    print(f"n={n} heavy: done packet (printed whole) {len(nav.render(e.CORE, run, s).encode())} bytes")
