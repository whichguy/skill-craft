#!/usr/bin/env python3
"""A fake `codex` for running the REAL `iterate.py --qualify` loop with no model (test/shiploop-e2e-adapter-engine.test.py): one program
answers every role (subject run, reviewer, judge, purpose check, improver), told apart by the opening of the prompt. The subject run
delivers the hello product and a done ShipLoop run. The reviewer finds one material discovery in an exploration unless
$FAKE_NO_DISCOVERY is set, and the judge supports it, so the same iteration goes on to a cycle. Its runs score `fidelity: unobserved`,
so a cycle decides UNDECIDED, never PROMOTE or DROP. Environment: CODEX_HOME (with auth.json), FAKE_STORE_DIR (the checkout's
skills/shiploop/scripts), FAKE_LOG."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

argv = sys.argv[1:]
LOG = os.environ.get("FAKE_LOG", os.devnull)
def log(**row):
    with open(LOG, "a") as handle:
        handle.write(json.dumps({"t": round(time.time(), 2), "pid": os.getpid(), **row}) + "\n")
def emit(event):
    print(json.dumps(event), flush=True)

if argv[:1] == ["--version"]:
    print("codex-cli 0.0.0-fake")
    sys.exit(0)
home = Path(os.environ["CODEX_HOME"])
state = home / "fake-plugin.json"
if argv[:3] == ["plugin", "marketplace", "add"]:
    state.write_text(json.dumps({"marketplace": argv[3]}))
    sys.exit(0)
if argv[:2] == ["plugin", "add"]:
    root = home / "plugins" / "cache" / "whichguy" / "skill-craft" / "9.9.9"
    (root / "skills" / "shiploop" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "shiploop" / "scripts" / "shiploop").write_text("")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    rows = [{"pluginId": "skill-craft@whichguy", "name": "skill-craft", "version": "9.9.9", "installed": True}] if state.exists() else []
    print(json.dumps({"installed": rows}))
    sys.exit(0)
assert argv[:2] == ["exec", "--json"], argv
cwd = argv[argv.index("-C") + 1]
os.chdir(cwd)
prompt = sys.stdin.buffer.read().decode("utf-8") if argv[-1] == "-" else argv[-1]

def finish(text):
    emit({"type": "thread.started", "thread_id": "fake-thread"})
    emit({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": text}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5, "output_tokens": 2}})
    sys.exit(0)

def fenced(obj):
    return "```json\n" + json.dumps(obj) + "\n```"

if "You are improving the ShipLoop skill" in prompt:
    record = re.search(r"Learning-Record: (LR-\d{8}-[0-9a-f]{6})", prompt).group(1)
    log(role="improver", cwd=cwd, record=record)
    readme = Path("skills/shiploop/README.md")
    readme.write_text(readme.read_text() + "\n<!-- fake candidate for %s -->\n" % record)
    subprocess.run(["git", "add", "skills/shiploop/README.md"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "candidate: say the default\n\nLearning-Record: %s\n" % record], check=True)
    finish(fenced({"applied": [{"title": "fake", "anchor": ["S-14"], "adversarial": []}], "skipped": [], "tests": "n/a",
                   "prediction": {"contract": "prediction/1", "record": record, "anchor": "S-14",
                                  "because": "a stated default replaces a pause, so fewer tokens are spent waiting",
                                  "effects": [{"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.3}],
                                  "guards": [{"case": "*", "measure": "accuracy", "direction": "not_down"}]}}))
if "You are checking whether one candidate change" in prompt:
    log(role="purpose", cwd=cwd)
    finish(fenced({"files": [{"path": "skills/shiploop/README.md", "serves": "yes", "why": "ok"}], "prediction_follows": True,
                   "prediction_note": "ok", "verdict": "aligned", "summary": "serves the record"}))
if "You are an independent second reviewer" in prompt:
    identity = re.search(r"identity is SHA-256 ([0-9a-f]{64})", prompt).group(1)
    block = re.search(r"payload follows:\n```json\n(.*?)\n```", prompt, re.DOTALL).group(1)
    ids = [d["id"] for d in json.loads(block).get("discoveries", [])]
    log(role="judge", cwd=cwd, ids=ids)
    finish(fenced({"review_sha256": identity, "assessments": [
        {"id": i, "status": "supported", "reason": "r", "evidence": ["result.json shows it"], "disposition": "implement"} for i in ids]}))
if "You are reviewing one end-to-end run" in prompt:
    run_dir = re.search(r"request in (\S+)/prompt\.txt", prompt).group(1)
    exploring = "/explore-" in run_dir and not os.environ.get("FAKE_NO_DISCOVERY")
    log(role="reviewer", cwd=cwd, run_dir=run_dir, exploring=exploring)
    discoveries = [{"id": "d1", "title": "Say the unattended default", "evidence": [{"reference": "transcript.md", "observation": "o",
        "interpretation": "i"}], "mission_anchor": {"clause_id": "S-14", "relationship": "supports", "challenge": None},
        "materiality": "material", "confidence": "high", "potential_impact": "x", "alternatives": ["a"], "next_experiment": "n",
        "target": "shiploop", "files": ["skills/shiploop/README.md"], "proposal": "p", "implementation_eligible": True,
        "proposed_disposition": "implement"}] if exploring else []
    finish("Reviewed.\n" + fenced({"outcome": "Delivered the request.", "version": 2, "learnings": [], "missing_considerations": [],
        "optimizations": [], "discoveries": discoveries, "harness": {k: {"answer": "keep", "proposals": []} for k in
        ("learning_retention", "further_learning", "evaluation_criteria")}}))

# The subject run: the hello product and a done ShipLoop run, as the support module's fake does.
log(role="subject", cwd=cwd, prompt_head=prompt[:60])
sys.path.insert(0, os.environ["FAKE_STORE_DIR"])
import shiploop_store as store  # noqa: E402
emit({"type": "thread.started", "thread_id": "codex-thread-1"})
emit({"type": "item.completed", "item": {"id": "item_0", "type": "command_execution",
      "command": "python3 /x/skills/shiploop/scripts/shiploop next", "aggregated_output": "ShipLoop navigator\n",
      "exit_code": 0, "status": "completed"}})
shutil.rmtree(".shiploop", ignore_errors=True)
Path("hello.py").write_text('print("Hello, world!")\n')
Path("test_hello.py").write_text("import subprocess, sys, unittest\nclass T(unittest.TestCase):\n    def test_it(self):\n        out = subprocess.run([sys.executable, 'hello.py'], capture_output=True, text=True).stdout\n        self.assertEqual(out.strip(), 'Hello, world!')\n")
Path(".shiploop").mkdir()
store.write_record(Path(".shiploop/state.md"), {"status": "done", "planning_review": "stage"})
Path(".shiploop/report.html").write_text("<html></html>")
Path(".gitignore").write_text(".shiploop/\n")
ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
if not Path(".git").exists():
    subprocess.run(["git", "init", "-q"], check=True)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "product"], check=True)
emit({"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": "Shipped."}})
emit({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5, "output_tokens": 2}})
