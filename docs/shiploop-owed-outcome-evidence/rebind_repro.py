"""Does a ShipLoop driving command between two stops reset the keepalive's no-progress memory?

A real ShipLoop run in a temporary directory and the recorded Claude hook payloads
(test/fixtures/shiploop-keepalive). Nothing advances the run between stops, so a different decision at the second
stop comes from the binding record, not from progress.

    python3 -I docs/shiploop-owed-outcome-evidence/rebind_repro.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/shiploop/scripts"
FIX = ROOT / "test/fixtures/shiploop-keepalive"
sys.path.insert(0, str(SCRIPTS))

tmp = Path(tempfile.mkdtemp(prefix="ka-repro-"))
os.environ.update(SHIPLOOP_KEEPALIVE_HOME=str(tmp / "state"), HOME=str(tmp / "home"),
                  XDG_CONFIG_HOME=str(tmp / "home/.config"))
os.environ.pop("SHIPLOOP_KEEPALIVE", None)
import shiploop_keepalive as ka

repo, run = tmp / "repo", tmp / "run"
repo.mkdir()
init = subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), "init", "--run-dir", str(run), "--repo", str(repo),
                       "--prompt", "Add a greeting script."], capture_output=True, text=True, check=False)
assert init.returncode == 0, init.stderr
MARKER = next(line for line in init.stdout.splitlines() if "SHIPLOOP-RUN" in line)


def payload(event, session, command=None, stdout=None):
    text = (FIX / f"claude-{event}.json").read_text().replace("__SESSION__", session).replace("__MARKER__", MARKER)
    data = json.loads(text)
    if command is not None:
        data["tool_input"]["command"] = command
    if stdout is not None:
        data["tool_response"]["stdout"] = stdout
    return data


def hook(event, data):
    out = ka.run_hook(event, "claude", json.dumps(data))
    return json.loads(out) if out else None


def verdict(reply):
    return "BLOCK" if reply and reply.get("decision") == "block" else "ALLOW"


def memory(session):
    binding = ka.load_binding("claude", session) or {}
    return {k: binding[k] for k in ("last_block_progress", "turn_blocks") if k in binding}


with mock.patch.object(ka, "DUPLICATE_WINDOW_SECONDS", 0):
    s = "A"
    hook("observe", payload("observe", s))
    print("A stop 1, nothing between            :", verdict(hook("stop", payload("stop", s))), memory(s))
    print("A stop 2, nothing between            :", verdict(hook("stop", payload("stop", s))), memory(s))

    s = "B"
    hook("observe", payload("observe", s))
    print("B stop 1                             :", verdict(hook("stop", payload("stop", s))), memory(s))
    hook("observe", payload("observe", s, command=str(SCRIPTS / "shiploop") + " next --run-dir " + str(run)))
    print("B binding after `shiploop next`      :", memory(s))
    print("B stop 2                             :", verdict(hook("stop", payload("stop", s))), memory(s))
    print("B stop 3, nothing between            :", verdict(hook("stop", payload("stop", s))), memory(s))

    s = "C"
    hook("observe", payload("observe", s))
    print("C stop 1                             :", verdict(hook("stop", payload("stop", s))), memory(s))
    hook("observe", payload("observe", s, command="python3 /x/until_loop_ephemeral.py next --state /y", stdout="{}"))
    print("C binding after a loop-runtime call  :", memory(s))
    print("C stop 2                             :", verdict(hook("stop", payload("stop", s))), memory(s))
