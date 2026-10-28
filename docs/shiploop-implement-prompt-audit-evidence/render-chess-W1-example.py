"""Render the implement packets ShipLoop now returns for the Salesforce chess case (run 2, work item W1), from the
run's real planning records: S1 (the DX project) and S2 (the rules engine)."""
import contextlib, glob, io, json, re, shutil, subprocess, sys
from pathlib import Path

WT = Path("/Users/dadleet/src/skill-craft/.claude/worktrees/impl-prompt-2d6ecc")
sys.path.insert(0, str(WT / "skills/shiploop/scripts"))
import shiploop_navigator as nav, shiploop_store as store  # noqa: E402

SRC = Path("/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/"
           "sfchess/live2/.shiploop-runs/work-20261017-005941-6661b3")
OUT = Path(sys.argv[1]); shutil.rmtree(OUT, ignore_errors=True)
repo, run = OUT / "repo", OUT / "run"; (repo / "docs/shiploop").mkdir(parents=True); run.mkdir()
for name in ("spec.md", "architecture.md", "environment.md"):
    shutil.copy(SRC / "worktree/docs/shiploop" / name, repo / "docs/shiploop" / name)
def git(*args): subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
git("init", "-q"); git("config", "user.email", "x@example.invalid"); git("config", "user.name", "example")
git("add", "-A"); git("commit", "-q", "-m", "docs(shiploop): spec, architecture and environment for the chess engine")

def result(prefix):
    path = glob.glob(str(SRC / "run/results" / (prefix + "*.md")))[0]
    return json.loads(re.search(r"```shiploop-state\n(.*?)\n```", Path(path).read_text(), re.S).group(1))["result"]
plan = result("nav-faabbb605cbf")          # plan: W1 and W2
step_plan = result("nav-3384b1a64cb9")     # W1's latest accepted step plan (after the test-stage revise)
test_spec = result("nav-bbbf0a391cce")     # W1's latest accepted test spec
checks = {"S1": next(c["command"] for c in step_plan["test_commands"] if c.get("criteria") == ["C1"]),
          "S2": next(c["command"] for c in step_plan["test_commands"] if c.get("criteria") == ["C9"])}
cards = {"S1": ["platforms/salesforce.md", "coding-practices.md#namespaces-and-placement"],
         "S2": ["platforms/salesforce.md", "coding-practices.md#composition-and-layers", "coding-practices.md#state"]}
steps = [dict({k: v for k, v in row.items() if k != "paths"}, check=checks[row["id"]], cards=cards[row["id"]])
         for row in step_plan["steps"]]
step_plan_result = {"outcome": "done", "summary": step_plan["summary"], "paths": step_plan["paths"],
                    "criteria": step_plan["criteria"], "test_commands": step_plan["test_commands"],
                    "follows": step_plan["follows"], "steps": steps,
                    "match": [{"what": "Apex: a public class with the SLChess prefix, public static methods, 4-space "
                                       "indent, and a class comment stating the FEN and UCI contract, per "
                                       "architecture.md ## Conventions", "like": None}]}
state_text = (SRC / "run/state.md").read_text()
prompt = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", state_text, re.S).group(1))["prompt"]
state = nav.new_state(str(repo), prompt, delegation="inline")

def emit(name):
    store.write_record(run / "state.md", state)
    shown = io.StringIO()
    with contextlib.redirect_stdout(shown):
        full = nav.emit(None, run, store.read_record(run / "state.md"))
    (OUT / (name + "-printed.txt")).write_text(shown.getvalue()); (OUT / (name + "-file.md")).write_text(full)
    print(name, "printed", len(shown.getvalue()), "file", len(full))

S1_DONE = {"outcome": "done", "summary": "sfdx-project.json names force-app at API 67.0; force-app/main/default is tracked.",
           "considerations": {key: "Rendering fixture: S1's accepted answer for " + key.replace("_", " ") + "."
                              for key in nav.CONSIDERATIONS},
           "evidence": [{"criterion": "C1", "ran_or_inspected": checks["S1"], "observed": "exit 0",
                         "output": "RUN/tests step-proof record", "establishes": "the project file shape",
                         "limits": "no deploy yet"}]}
rendered = 0
while rendered < 2:
    stage, action = nav.current_stage(state), nav.current_action(state)["id"]
    if stage == "implement":
        emit("S1" if rendered == 0 else "S2")
        rendered += 1
        if rendered == 2:
            break
        state = nav.apply(state, action, S1_DONE)
    else:
        body = {"outcome": "done", "summary": "Accepted " + stage + " (from Salesforce chess run 2)."}
        if stage == "plan":
            body["work_items"] = plan["work_items"]
        if stage == "step-plan":
            body = step_plan_result
        if stage == "test-spec":
            body = dict(body, test_cases=test_spec["test_cases"])
        state = nav.apply(state, action, body)
    if state.get("active_improve") is not None:
        state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
