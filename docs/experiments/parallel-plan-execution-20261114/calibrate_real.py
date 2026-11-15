#!/usr/bin/env python3
"""calibrate_real.py: the kit's real-repository mechanics (README Amendment A14) against known answers, with no model call.

Apparatus for docs/experiments/parallel-plan-execution-20261114. calibrate.py proves the kit, the launcher and the scorer on the toy write
fixture; this proves what A14 added to the kit on the real service (ticketfix.make_repo): the re-test of the merged tree, the landing of a
teammate's change, and the two recovery rules (redo, fix). Each scenario plays the parent and the workers itself with fixed edits, runs the
kit's own commands, and compares the ledger and the repository with what the registration says must happen.

  python3 calibrate_real.py                    prints one line per cell and "cells: N, off: M"; exit 0 only when off is 0
  python3 calibrate_real.py --mutations        breaks each new guard in a copy of the kit and requires the cells to notice (fail-first)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402
import ticketfix  # noqa: E402

KIT = Path(os.environ.get("PPE_KIT") or HERE / "dagkit.py")   # a mutated copy of the kit stands in here for --mutations
CELLS: list = []

NEW_TEST = """'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { manualClock } = require('../src/clock');
const { TicketStore } = require('../src/store');
test('{name}', () => {
  const tickets = new TicketStore({ clock: manualClock('2025-09-01T08:00:00.000Z') });
  const made = tickets.create({ title: 'x', requester: 'li@example.com', priority: 'normal' }, 'dana');
  assert.equal(made.id, 'T-0001');
});
"""


def cell(name: str, want, got) -> None:
    CELLS.append((name, want == got))
    print(f"{'ok ' if want == got else 'OFF'}  {name:<66} want {want!r:<26} got {got!r}")


class Trial:
    def __init__(self, tmp: Path, *, land: bool = False, policy: str = "fix", attempts: int = 4, land_patch: str | None = None):
        self.repo = tmp / "repo"
        self.base = ticketfix.make_repo(self.repo)
        self.run = tmp / "work" / "run"
        (tmp / "work").mkdir()
        plan = tmp / "plan.json"
        plan.write_text(json.dumps(ticketfix.plan()))
        args = ["init", "--plan", str(plan), "--run", str(self.run), "--repo", str(self.repo), "--workspace", "isolated", "--retest", "npm test --silent",
                "--on-failure", policy, "--max-attempts", str(attempts)]
        if land:
            patch = tmp / "landing.patch"
            patch.write_text(land_patch if land_patch is not None else ticketfix.landing_patch())
            args += ["--land", str(patch), "--land-message", ticketfix.LANDING_MESSAGE]
        self.kit(*args)

    def kit(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(KIT), *args], capture_output=True, text=True)

    def events(self, kind: str | None = None, step: str | None = None) -> list:
        found = dagkit.Run(self.run).events()
        return [e for e in found if (kind is None or e["kind"] == kind) and (step is None or e["step"] == step)]

    def begin(self, step: str) -> Path:
        done = self.kit("begin", "--run", str(self.run), "--step", step)
        found = re.search(r"Workspace \(work only inside it\): (\S+)", done.stdout)
        if not found:
            raise SystemExit(f"begin {step} printed no workspace: {done.stdout[-300:]}{done.stderr[-300:]}")
        return Path(found.group(1)), done.stdout

    def complete(self, step: str) -> subprocess.CompletedProcess:
        return self.kit("complete", "--run", str(self.run), "--step", step, "--result", json.dumps({"answer": 1, "method": "calibration"}))

    def ready(self, **env) -> dict:
        done = subprocess.run([sys.executable, str(KIT), "ready", "--run", str(self.run)], capture_output=True, text=True, env=dict(os.environ, **env))
        self.last = done
        return json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}

    def main_passes(self) -> bool:
        return ticketfix.suite_passed(self.repo) is not None and subprocess.run(["npm", "test", "--silent"], cwd=self.repo, capture_output=True).returncode == 0


def add_files(ws: Path, tag: str) -> None:
    (ws / "src" / f"zz{tag}.js").write_text(f"'use strict';\nmodule.exports = {{ tag: '{tag}' }};\n")
    (ws / "test" / f"zz{tag}.test.js").write_text(NEW_TEST.replace("{name}", f"zz{tag} adds a feature test"))
    # the test calls the store's creating method by the base's name, so it passes on the base and fails once a landing renames it


def resolve_markers(path: Path, replacement: str) -> None:
    """Resolve every conflict block of a file to the one line given (what a worker does with the markers)."""
    path.write_text(re.sub(r"<<<<<<< [^\n]*\n.*?=======\n.*?>>>>>>> [^\n]*\n", replacement + "\n", path.read_text(), flags=re.S))


def edit_first_line(ws: Path, text: str) -> None:
    path = ws / "README.md"
    lines = path.read_text().split("\n")
    lines[0] = text
    path.write_text("\n".join(lines))


def scenario_clean() -> None:
    print("\n-- S1: three clean branches, merged in completion order, the tests re-run after each merge")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp))
        spaces = {s: t.begin(s)[0] for s in ("T1", "T2", "T3")}
        for s, ws in spaces.items():
            add_files(ws, s)
        for s in ("T2", "T1", "T3"):   # completion order, not plan order
            t.complete(s)
        state = t.ready()
        cell("S1 merged in completion order", ["T2", "T1", "T3"], state["merged_now"])
        cell("S1 three re-tests, all green", [True, True, True], [e["detail"]["ok"] for e in t.events("retest")])
        cell("S1 the re-test counts the new tests (117 base + 3 new)", 120, t.events("retest")[-1]["detail"]["passed"])
        cell("S1 no conflict, no red re-test, no retry", (0, 0, 0), (len(t.events("conflict")), len(t.events("redtest")), len(t.events("retry"))))
        cell("S1 main holds all three files", True, all((t.repo / "src" / f"zz{s}.js").is_file() for s in ("T1", "T2", "T3")))
        cell("S1 verify is OK", "OK", t.kit("verify", "--run", str(t.run)).stdout.split()[1])


def scenario_conflict_fix() -> None:
    print("\n-- S2: a textual conflict under the fix rule: markers in the fix workspace, refused until resolved, then merged")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), policy="fix")
        ws1, ws2 = t.begin("T1")[0], t.begin("T2")[0]
        edit_first_line(ws1, "# Help desk tickets (one)")
        edit_first_line(ws2, "# Help desk tickets (two)")
        t.complete("T1"), t.complete("T2")
        state = t.ready()
        cell("S2 T1 merged, T2 conflicted", (["T1"], ["T2"]), (state["merged_now"], state["conflicted_now"]))
        retry = t.events("retry", "T2")[0]["detail"]
        cell("S2 the retry names the rule, the cause and the branch", ("fix", "conflict", "w-T2-1"), (retry["mode"], retry["cause"], retry["from_branch"]))
        cell("S2 main was put back (no merge in progress)", True, not (t.repo / ".git" / "MERGE_HEAD").exists())
        ws2b, text = t.begin("T2")
        opened = t.events("workspace", "T2")[-1]["detail"]
        cell("S2 the fix workspace holds the markers in README.md", (True, ["README.md"], False), ("<<<<<<<" in (ws2b / "README.md").read_text(), opened["unmerged"], opened["merge_ok"]))
        cell("S2 the task ends with the fix note, naming the file", True, "conflict markers" in text and "README.md" in text and "Do not start over" in text)
        refused = t.complete("T2")
        cell("S2 complete is refused while a marker remains", (3, "markers"), (refused.returncode, t.events("refused", "T2")[-1]["detail"]["category"]))
        resolve_markers(ws2b / "README.md", "# Help desk tickets (one and two)")
        cell("S2 complete is accepted once resolved", 0, t.complete("T2").returncode)
        state = t.ready()
        cell("S2 the resolved branch merges", ["T2"], state["merged_now"])
        cell("S2 main's README line is the resolution", "# Help desk tickets (one and two)", (t.repo / "README.md").read_text().split("\n")[0])
        cell("S2 the attempt count is 2", 2, dagkit.derive(json.loads((t.run / "plan.json").read_text()), t.events())["T2"]["attempt"])


def scenario_conflict_redo() -> None:
    print("\n-- S3: the same conflict under the redo rule: a fresh workspace from main's head, the work done again on top")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), policy="redo")
        ws1, ws2 = t.begin("T1")[0], t.begin("T2")[0]
        edit_first_line(ws1, "# Help desk tickets (one)")
        edit_first_line(ws2, "# Help desk tickets (two)")
        t.complete("T1"), t.complete("T2")
        t.ready()
        ws2b, text = t.begin("T2")
        cell("S3 the redo workspace is clean and already holds T1's line", "# Help desk tickets (one)", (ws2b / "README.md").read_text().split("\n")[0])
        cell("S3 the redo workspace is not a fix workspace", None, t.events("workspace", "T2")[-1]["detail"].get("fix"))
        cell("S3 the redo task ends with the conflict note", True, "conflicted with work that was already merged, in: README.md" in text)
        add_files(ws2b, "T2")
        t.complete("T2")
        cell("S3 the redone work merges", ["T2"], t.ready()["merged_now"])


def scenario_landing_red() -> None:
    print("\n-- S4: a teammate's rename lands first; a clean merge whose re-test is red is undone and fixed in place")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), land=True, policy="fix")
        ws1, ws2 = t.begin("T1")[0], t.begin("T2")[0]
        add_files(ws1, "T1")   # passes alone: it calls the base's name, create
        (ws2 / "src" / "zzT2.js").write_text("'use strict';\nmodule.exports = { tag: 'T2' };\n")
        t.complete("T1"), t.complete("T2")
        state = t.ready()
        landed = t.events("landed")[0]["detail"]
        cell("S4 the landing landed, green, as one commit before any merge", (True, True), (landed["ok"], t.events("landed")[0]["seq"] < t.events("merged")[0]["seq"]))
        cell("S4 the landing touches the store, the app and the tests", True, {"src/store.js", "src/app.js", "test/store.test.js"} <= set(landed["files"]))
        cell("S4 T1 failed its re-test (red), T2 merged", (["T2"], ["T1"]), (state["merged_now"], state["conflicted_now"]))
        cell("S4 one red test event, no textual conflict", (1, 0), (len(t.events("redtest", "T1")), len(t.events("conflict", "T1"))))
        retry = t.events("retry", "T1")[0]["detail"]
        cell("S4 the retry says fix, redtest, and carries the failing output", ("fix", "redtest", True), (retry["mode"], retry["cause"], "create is not a function" in retry["tail"] or "createTicket" in retry["tail"] or "TypeError" in retry["tail"]))
        cell("S4 main is green after the undo", True, t.main_passes())
        ws1b, text = t.begin("T1")
        opened = t.events("workspace", "T1")[-1]["detail"]
        cell("S4 the fix workspace merged main in cleanly (no markers) and the work is there", (True, [], True), (opened["merge_ok"], opened["unmerged"], (ws1b / "src" / "zzT1.js").is_file()))
        cell("S4 the fix task ends with the failing output", True, "the project's tests failed on the merged tree" in text and "Do not start over" in text)
        path = ws1b / "test" / "zzT1.test.js"
        path.write_text(path.read_text().replace(".create(", ".createTicket("))
        cell("S4 the fixed work completes", 0, t.complete("T1").returncode)
        cell("S4 the fixed work merges", ["T1"], t.ready()["merged_now"])
        cell("S4 main is green with all three changes", True, t.main_passes())
        cell("S4 the landing commit is in main's history", True, ticketfix.LANDING_MESSAGE in t.git_log())
        red = t.events("redtest", "T1")[0]["detail"]
        ref = subprocess.run(["git", "-C", str(t.repo), "rev-parse", "refs/candidates/T1-1"], capture_output=True, text=True).stdout.strip()
        cell("S4 the red candidate's exact commit is kept (event and ref agree, 40 hex)", True, bool(re.fullmatch(r"[0-9a-f]{40}", red["candidate"])) and red["candidate"] == ref)
        merged = t.events("merged", "T2")[0]["detail"]
        cell("S4 a merged event names the merge commit and main before it", True, bool(re.fullmatch(r"[0-9a-f]{40}", merged["commit"])) and merged["before"] != merged["commit"])
        cell("S4 the red re-test's undo seconds are recorded", True, red.get("reset_s") is not None)
        cell("S4 begin and complete record how long they waited for the lock", True, all("waited_s" in e["detail"] for e in t.events("start")) and all("waited_s" in e["detail"] for e in t.events("end")))
        cell("S4 a re-test keeps its earlier outputs (an empty list when it ran once)", True, all(isinstance(e["detail"].get("reruns"), list) for e in t.events("retest")))


def scenario_landing_conflict() -> None:
    print("\n-- S5: the landing and a worker change the same line: a textual conflict against the landing, fixed in place")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), land=True, policy="fix")
        ws1 = t.begin("T1")[0]
        path = ws1 / "src" / "store.js"
        path.write_text(path.read_text().replace("  create({ title, priority, requester }, actor) {", "  create({ title, priority, requester }, actor = 'system') {"))
        t.complete("T1")
        state = t.ready()
        cell("S5 T1 conflicted with the landing in the store", (["T1"], ["src/store.js"]), (state["conflicted_now"], t.events("conflict", "T1")[0]["detail"]["paths"]))
        ws1b, _ = t.begin("T1")
        cell("S5 the fix workspace has markers in src/store.js", True, "<<<<<<<" in (ws1b / "src" / "store.js").read_text())
        path = ws1b / "src" / "store.js"
        text = re.sub(r"<<<<<<< [^\n]*\n.*?=======\n.*?>>>>>>> [^\n]*\n", "  createTicket({ title, priority, requester }, actor = 'system') {\n", path.read_text(), flags=re.S)
        path.write_text(text)
        cell("S5 the resolved work completes", 0, t.complete("T1").returncode)
        cell("S5 and merges, green", (["T1"], True), (t.ready()["merged_now"], t.main_passes()))


def scenario_mergefail() -> None:
    print("\n-- S6: attempts used up: the merge fails and the step does not finish")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), policy="redo", attempts=1)
        ws1, ws2 = t.begin("T1")[0], t.begin("T2")[0]
        edit_first_line(ws1, "# one")
        edit_first_line(ws2, "# two")
        t.complete("T1"), t.complete("T2")
        t.ready()
        cell("S6 a mergefail event, no retry", (1, 0), (len(t.events("mergefail", "T2")), len(t.events("retry", "T2"))))
        state = dagkit.derive(json.loads((t.run / "plan.json").read_text()), t.events())
        cell("S6 T2 is failed, T1 merged", ("failed", True), (state["T2"]["state"], state["T1"]["merged"]))
        cell("S6 verify is not OK", True, t.kit("verify", "--run", str(t.run)).stdout.split()[1] != "OK")


def git_log(self) -> str:
    return subprocess.run(["git", "-C", str(self.repo), "log", "--format=%s"], capture_output=True, text=True).stdout


Trial.git_log = git_log


def scenario_noop_fix() -> None:
    print("\n-- S7: a fix attempt whose clean merge of main is the cure needs no edit (the re-test decides)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        flag = tmp / "red.flag"
        t = Trial(tmp, policy="fix")
        ws1 = t.begin("T1")[0]
        (ws1 / "test" / "zzflag.test.js").write_text("'use strict';\nconst { test } = require('node:test');\nconst assert = require('node:assert/strict');\nconst fs = require('node:fs');\n"
                                                      "test('flag file absent', () => assert.equal(fs.existsSync(process.env.PPE_FLAG_FILE || '/nonexistent/none'), false));\n")
        t.complete("T1")
        flag.write_text("x")
        state = t.ready(PPE_FLAG_FILE=str(flag))
        cell("S7 the merge is red while the flag stands, undone, offered again to be fixed", (["T1"], 1), (state.get("conflicted_now"), len(t.events("redtest", "T1"))))
        flag.unlink()
        ws1b, _ = t.begin("T1")
        opened = t.events("workspace", "T1")[-1]["detail"]
        cell("S7 the fix workspace took main in cleanly", (True, []), (opened["merge_ok"], opened["unmerged"]))
        done = t.complete("T1")
        cell("S7 complete is accepted with no new edit, recorded as a no-op", (0, True), (done.returncode, t.events("commit", "T1")[-1]["detail"].get("noop")))
        cell("S7 it merges, green", ["T1"], t.ready(PPE_FLAG_FILE=str(flag)).get("merged_now"))
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), policy="fix")
        ws1 = t.begin("T1")[0]
        done = t.complete("T1")
        cell("S7 a first attempt with nothing to commit is still refused as empty", (3, "empty"), (done.returncode, t.events("refused", "T1")[-1]["detail"]["category"]))


def scenario_landing_fault() -> None:
    print("\n-- S8: a landing that does not apply is an apparatus fault, reported by verify")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp), land=True, land_patch="diff --git a/nothing b/nothing\n--- a/nothing\n+++ b/nothing\n@@ -1 +1 @@\n-x\n+y\n")
        t.begin("T1")
        ws = t.events("workspace", "T1")[-1]["detail"]["path"]
        (Path(ws) / "src" / "zz.js").write_text("module.exports = 1;\n")
        t.complete("T1")
        t.ready()
        cell("S8 ready stops with the reason, and a landed event says it did not land", (True, False), (t.last.returncode != 0 and "landing patch does not apply" in (t.last.stdout + t.last.stderr), t.events("landed")[0]["detail"]["ok"]))
        verify = t.kit("verify", "--run", str(t.run)).stdout
        cell("S8 verify is FAIL and names the landing", (True, True), (verify.startswith("VERIFY FAIL"), "did not land" in verify))


def scenario_workspace_fault() -> None:
    print("\n-- S9: a workspace that cannot be made leaves the step not started, so a second begin works")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        t = Trial(tmp)
        (tmp / "work" / "ws").mkdir()
        (tmp / "work" / "ws" / "T1-1").write_text("in the way")
        failed = t.kit("begin", "--run", str(t.run), "--step", "T1")
        cell("S9 begin fails and no start is logged", (True, 0), (failed.returncode != 0, len(t.events("start", "T1"))))
        (tmp / "work" / "ws" / "T1-1").unlink()
        again = t.kit("begin", "--run", str(t.run), "--step", "T1")
        cell("S9 a second begin works and logs the start once", (0, 1), (again.returncode, len(t.events("start", "T1"))))


def scenario_merge_fault() -> None:
    print("\n-- S12: a merge that fails without a conflict is an apparatus fault, not a conflict to count")
    with tempfile.TemporaryDirectory() as tmp:
        t = Trial(Path(tmp))
        ws = t.begin("T1")[0]
        (ws / "src" / "zz.js").write_text("module.exports = 1;\n")
        t.complete("T1")
        subprocess.run(["git", "-C", str(t.repo), "worktree", "remove", "--force", str(ws)], capture_output=True)
        subprocess.run(["git", "-C", str(t.repo), "branch", "-D", "w-T1-1"], capture_output=True)
        t.ready()
        cell("S12 ready stops, a fault is logged, no conflict is counted", (True, 1, 0), (t.last.returncode != 0, len(t.events("fault")), len(t.events("conflict"))))
        cell("S12 verify names the apparatus fault", True, "apparatus fault" in t.kit("verify", "--run", str(t.run)).stdout)


SCENARIOS = {"clean": scenario_clean, "conflict_fix": scenario_conflict_fix, "conflict_redo": scenario_conflict_redo, "landing_red": scenario_landing_red,
             "landing_conflict": scenario_landing_conflict, "mergefail": scenario_mergefail,
             "noop_fix": scenario_noop_fix, "landing_fault": scenario_landing_fault, "workspace_fault": scenario_workspace_fault, "merge_fault": scenario_merge_fault}

# (name, scenarios that must notice, the kit's text, the broken text): each guard A14 added, broken in a copy
MUTATIONS = (
    ("a red re-test is not undone", ("landing_red",), '            reset_rc, reset_out = _git(repo, "reset", "--hard", before)\n', '            reset_rc, reset_out = 0, ""\n'),
    ("a red re-test is accepted", ("landing_red",), "    return rc == 0, text[-1500:]\n", "    return True, text[-1500:]\n"),
    ("a marker is committed as code", ("conflict_fix",), "        if found == 0:\n            return \"markers\"", "        if False:\n            return \"markers\""),
    ("the landing never lands", ("landing_red", "landing_conflict"), "    if not meta.get(\"land\") or any(e[\"kind\"] == \"landed\" for e in run.events()):\n        return\n",
     "    return\n"),
    ("a fix workspace does not merge main in", ("conflict_fix", "landing_red"), "        merge_rc, _ = _git(path, \"merge\", \"--no-edit\", \"-m\", f\"merge main into {step_id} attempt {attempt}\", base)\n",
     "        merge_rc = 0\n"),
    ("the recovery rule is always redo", ("conflict_fix", "landing_red"), 'mode=meta.get("on_failure", "redo")', 'mode="redo"'),
    ("a fix attempt that needs no edit is refused", ("noop_fix",), 'if ws.get("fix") and ws.get("merge_ok") and not ws.get("unmerged") and', 'if False and ws.get("fix") and ws.get("merge_ok") and not ws.get("unmerged") and'),
    ("a landing that did not land passes verify", ("landing_fault",), 'problems.append("the teammate\'s change did not land cleanly (an apparatus fault)")', "pass"),
    ("a merge error is counted as a conflict", ("merge_fault",), ("        if not paths:   # a merge that failed without a conflict", "        if abort_rc != 0:"),
     ("        if False:   # a merge that failed without a conflict", "        if False:")),
    ("a step's attempts are never used up", ("mergefail",), "    if attempt < meta.get(\"max_attempts\", MAX_ATTEMPTS):\n", "    if True:\n"),
)


def mutations() -> int:
    text = (HERE / "dagkit.py").read_text()
    missed = []
    for name, scenarios, old, new in MUTATIONS:
        olds, news = (old, new) if isinstance(old, tuple) else ((old,), (new,))
        if any(o not in text for o in olds):
            print(f"BAD  {name}: the text to break is not in the kit")
            missed.append(name)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "dagkit.py"
            broken = text
            for o, n in zip(olds, news):
                broken = broken.replace(o, n, 1)
            copy.write_text(broken)
            done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--only", ",".join(scenarios)], capture_output=True, text=True,
                                  env=dict(os.environ, PPE_KIT=str(copy)))
            found = re.search(r"cells: (\d+), off: (\d+)", done.stdout)
            off = int(found.group(2)) if found else -1
            caught = off != 0
            print(f"{'ok ' if caught else 'MISSED'}  broken kit: {name:<46} cells off: {off}")
            if not caught:
                missed.append(name)
    print(f"mutations: {len(MUTATIONS)}, missed: {len(missed)}")
    return 0 if not missed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="comma-separated scenario names: " + ", ".join(SCENARIOS))
    parser.add_argument("--mutations", action="store_true")
    args = parser.parse_args()
    if args.mutations:
        return mutations()
    for name in (args.only.split(",") if args.only else SCENARIOS):
        try:
            SCENARIOS[name]()
        except Exception as error:  # noqa: BLE001  (a scenario that cannot reach its end is a cell that is off, with the reason)
            cell(f"scenario {name} ran to its end", True, f"{type(error).__name__}: {str(error)[:70]}")
    off = [name for name, ok in CELLS if not ok]
    print(f"\ncells: {len(CELLS)}, off: {len(off)}")
    for name in off:
        print("  OFF", name)
    return 0 if not off else 1


if __name__ == "__main__":
    sys.exit(main())
