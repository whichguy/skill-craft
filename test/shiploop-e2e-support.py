"""No-model checks for the ShipLoop E2E harness (test/shiploop_e2e/).

Fake `grok` and `claude` executables stand in for the hosts, so these checks
cover the harness contract (empty start directory, isolated Grok profile,
argv, plugin and invocation grading, review parsing and the premise filter)
without launching a model. Every case passes its host and fake binary
explicitly and supplies a plugin build, so no real host or build is reached.
They say nothing about live ShipLoop behavior.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import http.server
import importlib.util
import io
import json
import shutil
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import stat
import subprocess
import sys
import types
import tempfile
import threading
import time
import unittest
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import boundary  # noqa: E402
import environment  # noqa: E402
import hosts  # noqa: E402
import iterate  # noqa: E402
import metrics  # noqa: E402
import packets
import progress  # noqa: E402
import review  # noqa: E402
import rollouts  # noqa: E402
import run  # noqa: E402
import status_card
# The fake hosts answer the Claude host's Anthropic route, which is also its default backend; the runs name it so they stay on it.
ANTHROPIC_ROUTE = {"claude": ("--backend", "anthropic")}
import scorecard  # noqa: E402
import fanout  # noqa: E402

# listeners.py is the module the leftover-listener tests are about. Where it does not exist (the state a failing test is first run
# in) only those tests may fail, each on an assertion (needs_listeners), so a missing module never takes the other tests down.
try:
    import listeners  # noqa: E402
except ModuleNotFoundError as missing:
    if missing.name != "listeners":
        raise
    listeners = None

# The real observer, kept before any test patches it: the classes that exercise lsof scope what it sees to their own folder.
REAL_OBSERVE = listeners.observe if listeners else None


def needs_listeners(cls):
    """Class decorator: while listeners.py does not exist every test of the class fails on this assertion, one by one."""
    inner = cls.setUp

    def setUp(self):
        self.assertIsNotNone(listeners, "test/shiploop_e2e/listeners.py does not exist")
        inner(self)

    cls.setUp = setUp
    return cls


def nothing_listens():
    """A patch that makes the machine's process table show no listener, so no test reads it (nothing to patch where listeners.py
    does not exist yet, and the older tests then run as before)."""
    return mock.patch.object(listeners, "observe", return_value=[]) if listeners else contextlib.nullcontext()

# Shared product writer for both fakes: the hello case's files plus a done run.
PRODUCT = f"""
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
def product():
    Path("hello.py").write_text('print("Hello, world!")\\n')
    Path("test_hello.py").write_text(
        "import subprocess, sys, unittest\\n"
        "class T(unittest.TestCase):\\n"
        "    def test_it(self):\\n"
        "        out = subprocess.run([sys.executable, 'hello.py'], capture_output=True, text=True).stdout\\n"
        "        self.assertEqual(out.strip(), 'Hello, world!')\\n")
    Path(".shiploop").mkdir()
    # A current run records its planning_review option; FAKE_PLANNING_REVIEW=absent leaves the key out, as a run before 1.22.0 does.
    state = {{"status": "done"}}
    if os.environ.get("FAKE_PLANNING_REVIEW", "stage") != "absent":
        state["planning_review"] = os.environ.get("FAKE_PLANNING_REVIEW", "stage")
    store.write_record(Path(".shiploop/state.md"), state)
    Path(".shiploop/report.html").write_text("<html></html>")
    # A finished run leaves its product committed, as ShipLoop's return does.
    import subprocess
    Path(".gitignore").write_text(".shiploop/\\n")
    ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    if not Path(".git").exists():
        subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "product"], check=True)
"""

# A TCP server in a process of its own, as a model's `node server.js &` is: its own session (a host's group kill cannot
# reach it), no stdio shared with its parent, and it expires by itself after two minutes. argv[1] is a port file that
# appears, complete, once the server listens ("<pid> <port>"); argv[2] == "ignore-term" makes it ignore SIGTERM. It accepts and
# drops each connection: a listener that never accepts resets some probes once its backlog fills, which made `answers` flaky.
LISTENER_SOURCE = (
    "import os, socket, sys, time\n"
    "s = socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1)\n"
    "if sys.argv[2:] == ['ignore-term']:\n"
    "    import signal; signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "open(sys.argv[1] + '.part', 'w').write('%d %d' % (os.getpid(), s.getsockname()[1]))\n"
    "os.rename(sys.argv[1] + '.part', sys.argv[1])\n"
    "s.settimeout(0.5)\n"
    "end = time.time() + 120\n"
    "while time.time() < end:\n"
    "    try:\n"
    "        s.accept()[0].close()\n"  # accept and drop, so a probe's connect is not queued behind earlier ones and reset
    "    except OSError:\n"
    "        pass\n")

# What both fake hosts can do with a listener: FAKE_LISTEN=<port file> leaves one running from the working directory, as a
# model's backgrounded server does; FAKE_PROBE_PORT=<port file> records, in FAKE_LOG.probe, whether that server still
# answers when the session starts.
LISTEN = f"""
def leak_a_listener():
    portfile = os.environ.get("FAKE_LISTEN")
    if not portfile:
        return
    import subprocess, time
    subprocess.Popen([sys.executable, "-c", {LISTENER_SOURCE!r}, portfile], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(200):
        if os.path.exists(portfile):
            break
        time.sleep(0.05)
def probe_a_port():
    portfile = os.environ.get("FAKE_PROBE_PORT")
    if not portfile or not os.path.exists(portfile):
        return
    import socket
    probe = socket.socket()
    probe.settimeout(2)
    answered = probe.connect_ex(("127.0.0.1", int(open(portfile).read().split()[1]))) == 0
    with open(os.environ["FAKE_LOG"] + ".probe", "a") as log:
        log.write("answers\\n" if answered else "refused\\n")
"""

# FAKE_MODE: done (product + done run), nothing (exit 0, no work), no-skill (done,
# but no ShipLoop command registered).
FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
{LISTEN}
argv = sys.argv[1:]
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{"argv": argv, "cwd_listing": os.listdir(".")}}))
mode = os.environ.get("FAKE_MODE")
plugin = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model", "claude_code_version": "0.0.1-fake",
                  "slash_commands": [] if mode == "no-skill" else ["skill-craft:shiploop"],
                  "plugins": [{{"name": "skill-craft", "path": plugin}}] if plugin else []}}), flush=True)
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": "shiploop next"}}}}]}}}}))
if os.environ.get("FAKE_COMMAND"):  # one more tool call, for a test that needs the run to do something
    print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                      "input": {{"command": os.environ["FAKE_COMMAND"]}}}}]}}}}))
leak_a_listener()
if mode in ("done", "no-skill"):
    product()
if mode == "active":
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
if mode == "api-error":
    # What the real CLI wrote when the API refused: subtype stays "success", is_error says otherwise.
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error",
                      "api_error_status": None, "stop_reason": "stop_sequence", "num_turns": 3,
                      "total_cost_usd": 0.0, "result": "API Error: Unable to connect to API: SSL certificate has expired"}}))
    sys.exit(1)
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 3, "total_cost_usd": 0.0,
                  "result": "done"}}))
"""

FAKE_GROK = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
{LISTEN}
argv = sys.argv[1:]
home = Path(os.environ["HOME"])
registry = home / ".grok" / "fake-plugins.txt"
if argv[:2] == ["plugin", "install"]:
    registry.write_text(f"  skill-craft-1: skill-craft [local: {{Path(argv[2]).resolve()}}]\\n")
    print("Installed 1 plugin(s)")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    print(registry.read_text() if registry.exists() else "")
    sys.exit(0)
os.chdir(argv[argv.index("--cwd") + 1])
probe_a_port()
prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text()
resumed = argv[argv.index("--resume") + 1] if "--resume" in argv else None
with open(os.environ["FAKE_LOG"] + ".sessions", "a") as log:
    log.write(json.dumps({{"resumed": resumed, "prompt": prompt, "pid": os.getpid()}}) + "\\n")
if os.environ.get("FAKE_MODE") == "crash-resumed" and resumed:
    sys.exit(1)  # a resumed session dies without writing any event
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{
    "argv": argv, "prompt": prompt, "cwd_listing": os.listdir("."), "home": str(home),
    "auth_is_symlink": (home / ".grok" / "auth.json").is_symlink(),
    "claude_skills": os.environ.get("GROK_CLAUDE_SKILLS_ENABLED")}}))
print(json.dumps({{"type": "available_commands", "tools": [], "commands": ["shiploop", "improve"]}}))
print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": "shiploop next"}}}}))
for chunk in ("Ship", "ped."):
    print(json.dumps({{"type": "text", "data": chunk}}))
leak_a_listener()
mode = os.environ.get("FAKE_MODE")
if mode == "done" or (mode == "resume" and resumed):
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)  # a resumed session finishes the same run
    product()
elif mode == "early" and not resumed:
    pass  # the first session ends before ShipLoop writes any state
elif mode == "early":
    product()
elif mode in ("hang", "hang-active") or (mode == "hang-resumed" and resumed):
    if mode == "hang-active":
        Path(".shiploop").mkdir(exist_ok=True)
        store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
    print(json.dumps({{"type": "session", "sessionId": "sess-1"}}), flush=True)
    import time
    time.sleep(600)  # killed by --timeout or by a requested stop
elif mode in ("resume", "stuck", "stuck-stop", "hang-resumed", "anon", "crash-resumed"):
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
end = {{"type": "end", "stopReason": "cancelled", "sessionId": "sess-1", "num_turns": 4, "total_cost_usd": 0.01}}
if mode == "anon":
    del end["sessionId"]  # the host never named its session: there is nothing to resume
print(json.dumps(end), flush=True)
if mode == "stuck-stop":
    # A person asks for a stop in the last instant of this session: after its end event, and the process leaves at once.
    # The request used to land before the end event and the interpreter's shutdown, a window the harness's poll could
    # fall in when the machine was busy and kill a host that was already finishing (3 of 16 parallel runs).
    (Path.cwd().parent / "stop").write_text("")
    os._exit(0)
"""


# A fake Codex CLI: plugin marketplace add / plugin add / plugin list --json, and
# `exec --json ... [resume ID] PROMPT` emitting Codex's JSON event stream.
FAKE_CODEX = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
argv = sys.argv[1:]
home = Path(os.environ["CODEX_HOME"])
state = home / "fake-plugin.json"
if argv[:3] == ["plugin", "marketplace", "add"]:
    if os.environ.get("FAKE_PLUGIN_FAIL"):  # a root with no .agents/plugins/marketplace.json
        print("no marketplace catalog in " + argv[3], file=sys.stderr)
        sys.exit(1)
    state.write_text(json.dumps({{"marketplace": argv[3]}}))
    sys.exit(0)
if argv[:2] == ["plugin", "add"]:
    root = home / "plugins" / "cache" / "whichguy" / "skill-craft" / "9.9.9"
    (root / "skills" / "shiploop" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "shiploop" / "scripts" / "shiploop").write_text("")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    rows = [{{"pluginId": "skill-craft@whichguy", "name": "skill-craft", "version": "9.9.9",
             "installed": True}}] if state.exists() else []
    print(json.dumps({{"installed": rows}}))
    sys.exit(0)
assert argv[:2] == ["exec", "--json"], argv
os.chdir(argv[argv.index("-C") + 1])
resumed = argv[argv.index("resume") + 1] if "resume" in argv else None
prompt = argv[-1]
Path(os.environ["FAKE_LOG"]).write_text(json.dumps({{"argv": argv, "prompt": prompt, "resumed": resumed,
    "cwd_listing": os.listdir("."), "codex_home": str(home),
    "auth_is_symlink": (home / "auth.json").is_symlink()}}))
def emit(event):
    print(json.dumps(event), flush=True)
emit({{"type": "thread.started", "thread_id": resumed or "codex-thread-1"}})
cli = "python3 /x/skills/shiploop/scripts/shiploop next"
emit({{"type": "item.completed", "item": {{"id": "item_0", "type": "command_execution", "command": cli,
      "aggregated_output": "ShipLoop navigator\\n", "exit_code": 0, "status": "completed"}}}})
if os.environ.get("FAKE_MODE") == "done":
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)  # a resumed session finishes the same run
    product()
emit({{"type": "item.completed", "item": {{"id": "item_1", "type": "agent_message", "text": "Shipped."}}}})
if os.environ.get("FAKE_ROLLOUT"):
    # Codex writes per-call usage only to its rollout files under CODEX_HOME, never to the event stream.
    import time
    rollout = home / "sessions" / "2026" / "10" / "04" / "rollout-fake.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
    rollout.write_text("".join(json.dumps({{"timestamp": stamp, "type": "token_usage_record", "payload": {{
        "thread_id": "t", "session_id": "t", "response_id": "r%d" % n,
        "usage": {{"total_tokens": 1000 * (n + 1)}}}}}}) + "\\n" for n in range(2)))
emit({{"type": "turn.completed", "usage": {{"input_tokens": 10, "cached_input_tokens": 5, "output_tokens": 2}}}})
"""

class HarnessCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.fakes = {}
        for name, body in (("claude", FAKE_CLAUDE), ("grok", FAKE_GROK), ("codex", FAKE_CODEX)):
            path = self.tmp / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            self.fakes[name] = path
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        # The CLI file a resume prompt names (run.shiploop_cli): a plugin build always carries one.
        self.cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        self.cli.parent.mkdir(parents=True)
        self.cli.write_text("")
        self.log = self.tmp / "fake-log.json"
        self.baselines = self.tmp / "baselines.jsonl"  # never the committed file
        os.environ["FAKE_LOG"] = str(self.log)
        self.addCleanup(os.environ.pop, "FAKE_MODE", None)
        auth = self.tmp / "auth.json"
        auth.write_text("{}")
        saved, hosts.GROK_AUTH = hosts.GROK_AUTH, auth
        self.addCleanup(setattr, hosts, "GROK_AUTH", saved)
        codex_home = self.tmp / "real-codex"
        codex_home.mkdir()
        (codex_home / "auth.json").write_text("{}")
        patched = mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)})
        patched.start()
        self.addCleanup(patched.stop)
        # No harness case reads the machine's process table: a listener another session (or a leaked server) holds
        # must not change a verdict here. The classes that exercise the real lsof scope what they see to their own folder.
        patch = nothing_listens()
        patch.__enter__()
        self.addCleanup(patch.__exit__, None, None, None)
        # No harness case starts a real browser: a case that declares the browser need would otherwise find one on this
        # machine. The classes that exercise the capability record pass a fake with --browser-bin.
        browser = mock.patch.object(environment, "autodetect_browser", return_value=None)
        browser.start()
        self.addCleanup(browser.stop)

    def invoke(self, host: str, mode: str, *extra: str) -> tuple[int, dict]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text())

    def seen(self) -> dict:
        return json.loads(self.log.read_text())












# The 2026-10-16 E2E audit's review control (docs/experiments/shiploop-e2e-audit-20261016/grading/): a reviewer that failed with
# no JSON and one that exited with only {"learnings": []} both gave an empty actionable list, and iterate.py counted each as a
# clean review of a passing run, so two of them stopped the loop as converged.
VALID_EMPTY_REVIEW = ('```json\n' + json.dumps({
    "outcome": "Delivered the request.", "learnings": [], "missing_considerations": [], "optimizations": [],
    "harness": {"learning_retention": {"answer": "keep", "proposals": []}}}) + '\n```')






ACTIONABLE_REVIEW = ('```json\n' + json.dumps({
    "outcome": "Delivered, with one gap.", "missing_considerations": [], "optimizations": [],
    "learnings": [{"title": "Name the port", "severity": "material", "preserves_premise": True, "evidence": "e", "proposal": "p",
                   "files": ["skills/shiploop/SKILL.md"]}],
    "harness": {"learning_retention": {"answer": "keep", "proposals": []}}}) + '\n```')



# The suite catalog's path, in two parts: the catalog gives a suite the source of every test helper its text names
# (its _suite_sources), and the catalog's own source names paths this suite does not cover.
SUITE_CATALOG = "test/suite" + "_catalog.py"












PORT_PROBE = ROOT / "docs" / "experiments" / "shiploop-e2e-audit-20261016" / "port-probe"
VALID_PAGE = ("require('http').createServer((req,res)=>{res.writeHead(200,{'content-type':'text/html'});"
              "res.end('<title>Battleship</title> candidate')}).listen(Number(process.env.PORT));\n")
# Ignores PORT: it listens on a port of its own choosing, as a product with a hard-coded port does.
ELSEWHERE = "require('http').createServer((req,res)=>res.end('<title>Battleship</title>')).listen(0, '127.0.0.1');\n"





BATTLESHIP_STUB = r'''
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
MODE = sys.argv[1]
FLEET = [[(0, c) for c in range(5)], [(2, c) for c in range(4)], [(4, c) for c in range(3)], [(6, 0), (7, 0)]]
games = {}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        gid = "g" if MODE == "constant-id" else str(len(games))
        games[gid] = {"shots": 0, "hit": set(), "over": False}
        self.send({"game": gid, **({"gameOver": True} if MODE == "audit" else {})})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        g, cell = games[str(body["game"])], (body["row"], body["col"])
        g["shots"] += 1
        if MODE == "all-sunk":
            return self.send({"result": "sunk", "gameOver": True})
        if MODE in ("audit", "constant-id"):
            return self.send({"result": "miss", "gameOver": True})
        if MODE == "no-fleet":
            return self.send({"result": "miss", "gameOver": g["shots"] >= 100})
        if MODE == "never-ends":
            return self.send({"result": "miss", "gameOver": False})
        if MODE == "bad-result":
            return self.send({"result": "splash", "gameOver": False})
        if g["over"] and MODE != "over-after-two-sunk":
            return self.send({"result": "miss", "gameOver": MODE != "restarts"})
        ship = next((s for s in FLEET if cell in s), None)
        result = "miss"
        if ship:
            first = not any(c in g["hit"] for c in ship)
            g["hit"].add(cell)
            whole = all(c in g["hit"] for c in ship)
            result = ("sunk" if first else "hit") if MODE == "sunk-first-hit" else "hit" if MODE == "never-sunk" else (
                "sunk" if whole else "hit")
        sunk = sum(all(c in g["hit"] for c in s) for s in FLEET)
        g["over"] = (sunk >= 1 if MODE == "over-after-first-sink" else sunk >= 2 if MODE == "over-after-two-sunk"
                     else all(c in g["hit"] for s in FLEET for c in s))
        self.send({"result": result, "gameOver": g["over"]})
HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
'''


# Independently written correct games for the oracle's calibration (build step 5): another id key, the standard five-ship
# fleet placed at random per game, extra fields in every reply, and a server that refuses shots after the end (allowed).
BATTLESHIP_ALT = r'''
import json, os, random, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
MODE = sys.argv[1]
SIZES = {"carrier": 5, "battleship": 4, "cruiser": 3, "submarine": 3, "destroyer": 2}
def place():
    taken, fleet = set(), {}
    for name, size in SIZES.items():
        while True:
            across = random.random() < 0.5
            r, c = random.randrange(10 if across else 11 - size), random.randrange(11 - size if across else 10)
            cells = [(r, c + i) if across else (r + i, c) for i in range(size)]
            if not taken & set(cells):
                taken |= set(cells); fleet[name] = cells; break
    return fleet
games = {}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, code=200):
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        gid = "x%d" % len(games)
        games[gid] = {"fleet": place(), "hit": set(), "shots": 0, "over": False}
        self.send({"gameId": gid, "size": 10})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        g = games[body["game"]]
        if g["over"]:
            return self.send({"error": "the game is over"}, 400) if MODE == "refuses-after-end" else self.send(
                {"result": "miss", "gameOver": True, "shots": g["shots"]})
        g["shots"] += 1
        cell = (body["row"], body["col"])
        name = next((n for n, cells in g["fleet"].items() if cell in cells), None)
        reply = {"result": "miss", "shots": g["shots"]}
        if name:
            g["hit"].add(cell)
            sunk = all(c in g["hit"] for c in g["fleet"][name])
            reply.update(result="sunk" if sunk else "hit", **({"ship": name} if sunk else {}))
        g["over"] = all(c in g["hit"] for cells in g["fleet"].values() for c in cells)
        self.send({**reply, "gameOver": g["over"]})
HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
'''



def write_engine_records(run_dir: Path, accepted: list, *, status: str = "done",
                         stage: str | None = None, inner: dict | None = None,
                         started: float | bool | None = None) -> None:
    """Write the state.md and timeline.json a run would leave behind.

    ``accepted`` is (action, stage, outcome, epoch-or-None); an action with None
    gets no acceptance stamp, which is how an unreadable or recreated timeline
    looks to the reader. ``started`` is the engine's start (default: the first stamp);
    False leaves it out, as in a run from before the pace line.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"navigator_protocol_version": 4, "status": status,
             "stage": stage or (accepted[-1][1] if accepted else "intake"),
             "history": [{"stage": s, "outcome": o, "workitem": None, "action": a}
                         for a, s, o, _t in accepted]}
    if inner:
        state.update(inner)
    (run_dir / "state.md").write_text("# state\n\n```shiploop-state\n"
                                      + json.dumps(state, indent=2) + "\n```\n")
    # Second precision, which is what the navigator's own _utc_now writes.
    def stamp(epoch: float) -> str:
        return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    begin = min((t for *_x, t in accepted if t is not None), default=0) if started is None else started
    (run_dir / "timeline.json").write_text(json.dumps(
        {**({} if begin is False else {"started": stamp(begin)}),
         "accepted": {a: stamp(t) for a, _s, _o, t in accepted if t is not None}}, indent=2) + "\n")












def write_stream_run(out: Path, stream: list, accepted: list, *, status: str = "done", stage: str | None = None,
                     inner: dict | None = None, first_event: float = 100.0,
                     rollout_files: list[list[str]] | None = None, started: float | bool | None = None,
                     binds: dict | None = None, timed: bool = True) -> Path:
    """The files of a run in `out`: the host stream with its runner timeline, ShipLoop's records and Codex rollouts.

    ``binds`` maps an action id to the modification time of its Improve child's `improve/<action>-bind.md`;
    ``timed=False`` leaves out the runner's timeline.jsonl. Returns the ShipLoop run directory."""
    for number, lines in enumerate(rollout_files or []):
        write_rollout(out, f"{number}", lines)
    run_dir = out / "run"
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
    if timed:
        (out / "timeline.jsonl").write_text("".join(
            json.dumps({"line": n, "t": first_event + n}) + "\n"
            for n, e in enumerate(stream) if e.get("type") not in ("text", "thought")))
    write_engine_records(run_dir, accepted, status=status, stage=stage, inner=inner, started=started)
    for action, mtime in (binds or {}).items():
        bind = run_dir / "improve" / f"{action}-bind.md"
        bind.parent.mkdir(parents=True, exist_ok=True)
        bind.write_text("bound\n")
        os.utime(bind, (mtime, mtime))
    return run_dir


def collect_stream(stream: list, accepted: list, **kw) -> dict:
    """metrics.collect over a hand-built host stream, one second between events, ShipLoop records beside it.

    ``rollout_files`` are Codex rollouts (one list of lines each) written under the run's own CODEX_HOME;
    the other keywords are write_stream_run's."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        run_dir = write_stream_run(out, stream, accepted, **kw)
        return metrics.collect(out, run_dir)


def codex_stream(commands: int) -> list[dict]:
    """What a Codex session looks like after the harness's translator: tool calls and one `end`, no usage events."""
    translate = hosts.host("codex").translator()
    raw = [{"type": "thread.started", "thread_id": "t1"}]
    raw += [{"type": "item.completed", "item": {"id": f"item_{n}", "type": "command_execution",
                                                "command": f"echo {n}", "aggregated_output": "ok\n",
                                                "exit_code": 0, "status": "completed"}} for n in range(commands)]
    raw.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5,
                                                    "output_tokens": 2}})
    return [json.loads(line) for event in raw for line in translate((json.dumps(event) + "\n").encode())]


def claude_stream(commands: list[str]) -> list[dict]:
    """A Claude session: tool calls are tool_use blocks, with a per-message usage snapshot."""
    stream = []
    for n, command in enumerate(commands):
        stream.append({"type": "assistant", "message": {
            "id": f"m{n}", "usage": {"input_tokens": 10, "output_tokens": 3},
            "content": [{"type": "tool_use", "id": f"u{n}", "name": "Bash", "input": {"command": command}}]}})
        stream.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"u{n}", "content": "error: refused"}]}})
    stream.append({"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
                   "stop_reason": "end_turn", "num_turns": len(commands), "total_cost_usd": 1.0})
    return stream


# Claude calls recorded in the round-1 Sonnet runs, cut to a compact extract (docs/experiments/claude-tool-blocks-20261008).
TOOL_BLOCKS = ROOT / "docs" / "experiments" / "claude-tool-blocks-20261008"


def recorded_calls(*names: str, run: str = "battleship") -> list[dict]:
    """The recorded Claude events (a message's thinking event, its tool_use and the tool_result) of the named calls,
    in the order they were recorded. ``run`` is battleship or checkers."""
    file = f"{run}-sonnet-calls.jsonl"
    manifest = json.loads((TOOL_BLOCKS / "manifest.json").read_text())[file]
    events = [json.loads(line) for line in (TOOL_BLOCKS / file).read_text().splitlines()]
    return [events[n] for n in sorted({n for name in names for n in manifest[name]["lines"]})]


def recorded_command(name: str, run: str = "battleship") -> str:
    """The shell command of one recorded Bash call."""
    return next(b["input"]["command"] for e in recorded_calls(name, run=run) if e["type"] == "assistant"
                for b in e["message"]["content"] if b["type"] == "tool_use")


def with_command(events: list[dict], command: str) -> list[dict]:
    """The same recorded events with the Bash command of their tool_use replaced (its result is kept as recorded)."""
    events = json.loads(json.dumps(events))
    for e in events:
        for b in e["message"]["content"] if e["type"] == "assistant" else []:
            if b["type"] == "tool_use":
                b["input"]["command"] = command
    return events


def with_result(events: list[dict], text: str) -> list[dict]:
    """The same recorded events with the text of their last tool_result replaced."""
    events = json.loads(json.dumps(events))
    last = [b for e in events if e["type"] == "user" for b in e["message"]["content"]][-1]
    last["content"] = text
    return events


CLAUDE_END = {"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
              "stop_reason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}







class PrintedCase(HarnessCase):
    """A harness case that keeps what run.main printed, so the report can be asserted on."""

    def invoke_printed(self, host: str, mode: str, *extra: str) -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}-{len(list(self.tmp.glob('out-*')))}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def stopped(self, printed: str) -> str:
        return next(line for line in printed.splitlines() if line.startswith("  stopped"))

    def last_row(self) -> dict:
        return json.loads(self.baselines.read_text().splitlines()[-1])








# What ShipLoop leaves behind when a run ends before it has returned anything: its empty baseline commit and a
# run directory that is done. The product (a file) never reached the source checkout.
FAKE_CLAUDE_EMPTY_BASELINE = f"""#!{sys.executable}
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
argv = sys.argv[1:]
plugin = argv[argv.index("--plugin-dir") + 1]
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model",
                  "slash_commands": ["skill-craft:shiploop"], "plugins": [{{"name": "skill-craft", "path": plugin}}]}}))
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": "shiploop next"}}}}]}}}}))
subprocess.run(["git", "init", "-q"], check=True)
subprocess.run(["git", "-c", "user.name=ShipLoop", "-c", "user.email=shiploop@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty",
                "-m", "Empty baseline for the first ShipLoop run"], check=True)
Path(".git/info").mkdir(exist_ok=True)
Path(".git/info/exclude").write_text(".shiploop/\\n")  # the run directory is not a product path
Path(".shiploop").mkdir()
store.write_record(Path(".shiploop/state.md"), {{"status": "done"}})
Path(".shiploop/report.html").write_text("<html></html>")
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 1, "total_cost_usd": 0.0, "result": "done"}}))
"""











def codex_session(items: list[dict], *, end: bool = True, thread: str = "t1") -> list[dict]:
    """One Codex session after the harness's translator; ``end=False`` is a session killed before turn.completed."""
    translate = hosts.host("codex").translator()
    raw = [{"type": "thread.started", "thread_id": thread}]
    raw += [{"type": "item.completed", "item": item} for item in items]
    if end:
        raw.append({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 5,
                                                        "output_tokens": 2}})
    return [json.loads(line) for event in raw for line in translate((json.dumps(event) + "\n").encode())]


def rollout_line(kind: str, t: float, payload: dict) -> str:
    """One Codex rollout record, stamped the way Codex stamps it (UTC, milliseconds, Z)."""
    stamp = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(timespec="milliseconds")
    return json.dumps({"timestamp": stamp.replace("+00:00", "Z"), "type": kind, "payload": payload})


def usage_line(t: float, thread: str, session: str, response: str, total: int, output: int = 100,
               reasoning: int | None = None) -> str:
    return rollout_line("token_usage_record", t, {
        "thread_id": thread, "session_id": session, "response_id": response,
        "usage": {"input_tokens": total - output, "output_tokens": output, "total_tokens": total,
                  **({} if reasoning is None else {"reasoning_output_tokens": reasoning})}})


def count_line(t: float, window: int, total: int, *, after_compaction: bool = False) -> str:
    """The token_count event that follows a call (or, after a compaction, reports the shrunken context)."""
    last = {"input_tokens": 0 if after_compaction else total - 100, "output_tokens": 100, "total_tokens": total}
    return rollout_line("event_msg", t, {"type": "token_count", "info": {
        "model_context_window": window, "last_token_usage": last, "total_token_usage": {"total_tokens": total}}})


def compacted_line(t: float, request: str) -> str:
    return rollout_line("compacted", t, {"message": "", "compaction_response_id": request, "replacement_history": []})


def write_rollout(out: Path, name: str, lines: list[str]) -> Path:
    path = out / "home" / ".codex" / "sessions" / "2026" / "10" / "04" / f"rollout-{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def thread_calls(thread: str, session: str, window: int, calls: list[tuple]) -> list[str]:
    """(time, response id, total, request?) rows as the records Codex writes: a call is a usage record and a
    token_count; a compaction request is a usage record with no token_count, then the compacted record and the
    token_count of the shrunken context."""
    lines = []
    for t, response, total, request in calls:
        lines.append(usage_line(t, thread, session, response, total))
        if request:
            lines += [compacted_line(t + 0.01, response), count_line(t + 0.02, window, 500, after_compaction=True)]
        else:
            lines.append(count_line(t + 0.01, window, total))
    return lines


# Two threads: the root thread (6 calls, 2 compactions) and a sub-agent forked from it (3 calls, 1 compaction).
# The compaction requests carry the heaviest totals (9500, 8000, 12000): a request holds the whole context.
ROOT_THREAD = [(1000, "r1", 1000, False), (1015, "r2", 2000, False), (1020, "r3", 9000, False),
               (1030, "rq1", 9500, True), (1040, "r4", 3000, False), (1050, "r5", 4000, False),
               (1060, "rq2", 8000, True), (1070, "r6", 1500, False)]
SUB_THREAD = [(1025, "s1", 5000, False), (1045, "s2", 6000, False), (1055, "sq1", 12000, True),
              (1065, "s3", 7000, False)]


def two_thread_rollouts() -> list[list[str]]:
    root = [rollout_line("session_meta", 999, {"id": "root"}), *thread_calls("root", "root", 10000, ROOT_THREAD)]
    root.insert(5, count_line(1020.02, 10000, 9000))  # a repeated token_count: not a call
    root.append('{"timestamp": "2026-10-04T')  # the half-written last line of a rollout a live run still writes
    # The sub-agent's file opens with its parent's last compacted record, stamped at the fork: its request is
    # a record in the parent's file, so it is inherited history and not this thread's compaction.
    sub = [rollout_line("session_meta", 1015, {"id": "sub", "forked_from_id": "root"}),
           compacted_line(1015.0, "rq1"), *thread_calls("sub", "root", 20000, SUB_THREAD)]
    return [root, sub]







def codex_command(n: int, command: str = "echo ok", output: str = "ok\n", code: int = 0) -> dict:
    return {"id": f"item_{n}", "type": "command_execution", "command": command, "aggregated_output": output,
            "exit_code": code, "status": "completed" if code == 0 else "failed"}



















LSOF_LISTENING = """p969
crapportd
u501
f14
n*:58318
f15
n*:58318
p2059
cOllama
u501
f3
n127.0.0.1:11434
p300
cmDNSResponder
u0
f7
n*:5353
p63973
cnode
u501
f12
n*:3457
f13
n[::1]:3457
"""
LSOF_CWD = "p2059\nfcwd\nn/\np63973\nfcwd\nn/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work\n"
PS_COMMANDS = ("  300 /usr/sbin/mDNSResponder\n 2059 /Applications/Ollama.app/Contents/Resources/ollama serve\n"
               "63973 node /Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/.shiploop-runs/work-1/worktree/server.js\n")


def listener(pid: int, cwd: str | None, argv: str = "", ports: tuple = (3457,)) -> dict:
    return {"pid": pid, "command": argv.split()[0] if argv else "x", "ports": list(ports), "cwd": cwd, "argv": argv}



needs_lsof = unittest.skipUnless(shutil.which("lsof") and shutil.which("ps"),
                                 "the real-process tests need lsof and ps on PATH (the pure parse and selection tests still run)")


def end_quietly(proc: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError):
        proc.kill()
    proc.wait()
    if proc.stdout:
        proc.stdout.close()


def kill_leaked(portfile: Path) -> None:
    """Stop a listener a fake host left behind (it was reparented, so there is no Popen); it also expires on its own."""
    if portfile.exists():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(portfile.read_text().split()[0]), 9)


def answers(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(2)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def refuses_soon(port: int, seconds: float = 5.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not answers(port):
            return True
        time.sleep(0.05)
    return False


def isolate_git(case: unittest.TestCase) -> None:
    """A fake host runs real git: neither the machine's system nor its global config (signing, an lfs filter) may reach it."""
    patched = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
    patched.start()
    case.addCleanup(patched.stop)













def grok_usage(count: int, output: int = 100, reasoning: int = 40) -> list[dict]:
    """`count` per-call usage events, the shape Grok writes (and the Codex translator does not)."""
    return [{"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": output, "reasoning_tokens": reasoning}}
            for _ in range(count)]


# A planning window: the host's first event is at 1000, the engine starts at 1030, and the first accepted test-spec is 400 s
# after the host began (370 s after the engine did). The implement row is after the window.
PLANNING_ROWS = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", 1250),
                 ("a-ts", "test-spec", "done", 1400), ("a-impl", "implement", "done", 1500)]











def _tests_from_namespace(loader, module_name, namespace, pattern=None):
    suite = unittest.TestSuite()
    for name, candidate in sorted(namespace.items()):
        if not isinstance(candidate, type):
            continue
        if candidate.__module__ != module_name or not issubclass(candidate, unittest.TestCase):
            continue
        if loader.getTestCaseNames(candidate):
            suite.addTests(loader.loadTestsFromTestCase(candidate))
    return suite


def _tests_from_modules(loader, modules, pattern=None):
    classes = []
    for module in modules:
        for name, candidate in vars(module).items():
            if not isinstance(candidate, type):
                continue
            if candidate.__module__ != module.__name__ or not issubclass(candidate, unittest.TestCase):
                continue
            classes.append((name, candidate))
    suite = unittest.TestSuite()
    for name, candidate in sorted(classes, key=lambda item: item[0]):
        if loader.getTestCaseNames(candidate):
            suite.addTests(loader.loadTestsFromTestCase(candidate))
    return suite


_COMPONENT_MODULE_SPECS = {
    "analysis": ("shiploop_e2e_analysis_tests", "shiploop-e2e-analysis.test.py"),
    "hosts": ("shiploop_e2e_hosts_tests", "shiploop-e2e-hosts.test.py"),
    "resources": ("shiploop_e2e_resources_tests", "shiploop-e2e-resources.test.py"),
}


def _load_component_module(component):
    module_name, filename = _COMPONENT_MODULE_SPECS[component]
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded
    module_path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load ShipLoop E2E component {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]
        raise
    return module
