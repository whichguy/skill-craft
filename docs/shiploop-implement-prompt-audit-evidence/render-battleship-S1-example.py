"""Render the implement packet ShipLoop would return for Battleship step S1, from that run's real planning records."""
import contextlib, io, json, re, shutil, subprocess, sys
from pathlib import Path

WT = Path("/Users/dadleet/src/skill-craft/.claude/worktrees/impl-prompt-2d6ecc")
sys.path.insert(0, str(WT / "skills/shiploop/scripts"))
import shiploop_navigator as nav, shiploop_store as store  # noqa: E402

SRC = Path("/Users/dadleet/e2e-runs/20261016/battleship-e2eaudit-4dd3b4b4/.shiploop-runs/work-20261017-041336-c46c7d")
OUT = Path(sys.argv[1]); shutil.rmtree(OUT, ignore_errors=True)
repo, run = OUT / "repo", OUT / "run"; (repo / "docs/shiploop").mkdir(parents=True); run.mkdir()
for name in ("spec.md", "architecture.md", "environment.md"):
    shutil.copy(SRC / "worktree/docs/shiploop" / name, repo / "docs/shiploop" / name)
def git(*args): subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
git("init", "-q"); git("config", "user.email", "x@example.invalid"); git("config", "user.name", "example")
git("add", "-A"); git("commit", "-q", "-m", "docs(shiploop): spec, architecture and environment for Battleship")
(repo / "README.md").write_text("# Battleship\n"); git("add", "-A")
git("commit", "-q", "-m", "chore: start the Battleship repository\n\nLesson: node --test runs every .js file under test/.")

def result(action):
    text = (SRC / "run/results" / (action + ".md")).read_text()
    return json.loads(re.search(r"```shiploop-state\n(.*?)\n```", text, re.S).group(1))["result"]
plan = result("nav-d473c101df4d43559670aeac7ce8745e")
spec_cases = next(result(p.stem) for p in (SRC / "run/results").glob("nav-*.md")
                  if '"stage": "test-spec"' in p.read_text())
checks = {
    "S1": "node -e \"const g=require('./game.js'); for (const k of ['SIZE','FLEET','placeFleet','createGame','fire',"
          "'createStore','GameError']) if (!(k in g)) process.exit(1)\"",
    "S2": "node -e \"const h=require('fs').readFileSync('public/index.html','utf8'); "
          "process.exit(/<title>Battleship<\\/title>/.test(h) && /id=\\\"board\\\"/.test(h) ? 0 : 1)\"",
    "S3": "node --check server.js && node -e \"const s=require('./server.js'); process.exit(typeof s.createServer==='function' ? 0 : 1)\"",
}
cards = {"S1": ["coding-practices.md#composition-and-layers", "coding-practices.md#namespaces-and-placement",
                "platforms/node-express.md"],
         "S2": ["platforms/ui.md", "coding-practices.md#localization"],
         "S3": ["platforms/node-express.md", "coding-practices.md#security"]}
steps = [dict({k: v for k, v in row.items() if k != "paths"}, check=checks[row["id"]], cards=cards[row["id"]])
         for row in plan["steps"]]
step_plan = {"outcome": "done", "summary": plan["summary"], "paths": plan["paths"], "criteria": plan["criteria"],
             "test_commands": plan["test_commands"], "follows": plan["follows"], "steps": steps,
             "match": [{"what": "CommonJS module with 'use strict' and a contract comment on each export, per "
                                "architecture.md ## Conventions", "like": None}]}

prompt = (SRC / "run/state.md").read_text()
prompt = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", prompt, re.S).group(1))["prompt"]
state = nav.new_state(str(repo), prompt, delegation="inline")
while nav.current_stage(state) != "implement":
    stage, action = nav.current_stage(state), nav.current_action(state)["id"]
    body = {"outcome": "done", "summary": "Accepted " + stage + " (from the 2026-10-16 Battleship run)."}
    if stage == "plan":
        body["work_items"] = [{"id": "W1", "title": "Build Battleship server, rules module, page and node:test suite"}]
    if stage == "step-plan":
        body = step_plan
    if stage == "test-spec":
        body = dict(body, test_cases=spec_cases["test_cases"])
    state = nav.apply(state, action, body)
    if state.get("active_improve") is not None:
        state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
store.write_record(run / "state.md", state)
shown = io.StringIO()
with contextlib.redirect_stdout(shown):
    full = nav.emit(None, run, store.read_record(run / "state.md"))
(OUT / "printed-head.txt").write_text(shown.getvalue())
(OUT / "packet-file.md").write_text(full)
print("printed", len(shown.getvalue()), "file", len(full))
