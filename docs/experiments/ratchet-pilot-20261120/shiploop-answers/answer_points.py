"""One line per delivery of a round: whether it is past the stage that applies an answer, what the stand-in sent, and
what that stage's accepted result records.  argv: ROOT NAME...  Exit 0 when every named delivery is past the stage or
has ended; 1 otherwise."""
import glob
import json
import os
import re
import sys

root, names = sys.argv[1], sys.argv[2:]
home = os.path.expanduser("~")
pending = 0
for name in names:
    out = os.path.join(root, name)
    runs = sorted(glob.glob(out + "/.shiploop-runs/*/run"), key=lambda r: os.path.getsize(r + "/state.md") if os.path.exists(r + "/state.md") else 0)
    ended = os.path.exists(out + ".exit")
    line = [name]
    state = {}
    if runs:
        try:
            with open(runs[-1] + "/state.md", errors="replace") as handle:
                state_text = handle.read()
            state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", state_text, re.DOTALL).group(1))
        except (OSError, AttributeError, ValueError):
            state = {}
    history = state.get("history") or []
    accepted = state.get("accepted") or {}
    done = [r for r in history if r.get("stage") == "test-strategy" and r.get("outcome") == "done"]
    past = bool(done) and state.get("stage") != "test-strategy" and not state.get("active_improve")
    if not (past or ended):
        pending += 1
    ended_text = ""
    if ended:
        with open(out + ".exit") as handle:
            ended_text = " ENDED exit " + handle.read().strip()
    line.append(f"stage {state.get('stage')} rev {state.get('revision')}" + ended_text)
    try:
        with open(out + "-requester.json") as handle:
            req = json.load(handle)
    except (OSError, ValueError):
        req = {}
    choice = req.get("choice") or {}
    line.append(f"stand-in: chose row {choice.get('chosen')} selector {choice.get('selector')} tied {choice.get('tied')} note {json.dumps(req.get('note'))[:90]} | {str(req.get('ended'))[:110]}")
    if done:
        rows = (accepted.get(done[-1]["action"]) or {}).get("answers")
        line.append("accepted answers: " + json.dumps(rows)[:420])
    notes = sorted(os.path.basename(p) for p in glob.glob(runs[-1] + "/owner-notes/N*.md")) if runs else []
    refusals = []
    if runs and os.path.exists(runs[-1] + "/trace.jsonl"):
        with open(runs[-1] + "/trace.jsonl", errors="replace") as handle:
            for l in handle:
                try:
                    r = json.loads(l)
                except ValueError:
                    continue
                if r.get("kind") == "command" and r.get("exit") and r.get("error") and "answers" in str(r["error"]):
                    refusals.append(" ".join(str(r["error"]).split())[:200])
    line.append(f"notes {notes} | refusals naming answers: {len(refusals)}" + ("".join("\n      " + x for x in refusals[:3])))
    print(("\n   ".join(line)).replace(home, "~"))
sys.exit(1 if pending else 0)
