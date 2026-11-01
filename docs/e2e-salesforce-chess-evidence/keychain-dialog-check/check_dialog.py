#!/usr/bin/env python3
"""Does a throwaway-HOME host environment raise a macOS "Keychain Not Found" dialog?

usage: check_dialog.py <checkout holding test/shiploop_e2e> <scratch dir holding windows_of.js>

Uses the harness's own environment builder (hosts.host("codex").env) and wrapper writer (run.write_model_bin), so what it
checks is what a run gets. A dialog is looked for without any permission: a SecurityAgent process (macOS starts one to show
the dialog), a `security *-generic-password` process waiting on it, and the windows SecurityAgent owns (the window server
lists every window's owner and on-screen state without Screen Recording access).

Stages: control (the old behaviour, one command, removed at once, to show the check can see a dialog), fixed (the commands the
trials ran), wrapper (the guarded case's sf through sf_guard.py with the real HOME), chrome (headless, as the UI check
launches it: Playwright with the installed Google Chrome).
"""
import glob
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CHECKOUT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(CHECKOUT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import run  # noqa: E402

VAR = "SF_USE_GENERIC_UNIX_KEYCHAIN"
QUERY = "SELECT Id FROM Organization LIMIT 1"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WRITER = r"security (add|find|delete)-generic-password"


def pids(pattern: str, exact: bool = False) -> list:
    done = subprocess.run(["pgrep", "-x" if exact else "-f", pattern], capture_output=True, text=True)
    return sorted(int(x) for x in done.stdout.split())


def agent_windows(agents: list) -> list:
    if not agents:
        return []
    out = subprocess.run(["osascript", "-l", "JavaScript", str(SCRATCH / "windows_of.js"), *map(str, agents)],
                         capture_output=True, text=True, timeout=60).stdout
    try:
        return json.loads(out)
    except ValueError:
        return [{"error": out.strip()[:80]}]


def snapshot() -> dict:
    agents = pids("SecurityAgent", exact=True)
    return {"SecurityAgent": agents, "waiting_keychain_writers": pids(WRITER), "agent_windows": agent_windows(agents)}


def clear(snap: dict) -> bool:
    return not (snap["SecurityAgent"] or snap["waiting_keychain_writers"])


def show(snap: dict) -> str:
    return "NONE" if clear(snap) else json.dumps(snap)


START = snapshot()
print(f"start: SecurityAgent {START['SecurityAgent']}, waiting keychain writers {START['waiting_keychain_writers']}")
if not clear(START):
    sys.exit("a dialog or a waiting keychain writer exists already: answer it first, then rerun")


def fresh_home(tag: str) -> tuple:
    base = Path(tempfile.mkdtemp(prefix=f"{tag}-", dir=SCRATCH))
    work = base / "work"
    work.mkdir()
    return base / "home", work


def run_to_end(argv, env, cwd, timeout=120) -> tuple:
    began = time.time()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        status = f"exit {proc.returncode}"
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
        status = "TIMEOUT"
    return status, round(time.time() - began, 1), out


def reason(out: str) -> str:
    for key in ("NamedOrgNotFoundError", "No authorization information"):
        if key in out:
            return key
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[-1][:70] if lines else ""


# ---------------------------------------------------------------- control: the old behaviour, once
print("\n== control: the old behaviour (no variable), one command, fresh throwaway HOME")
home, work = fresh_home("control")
env = hosts.host("codex").env(home)
assert env.pop(VAR) == "true"
proc = subprocess.Popen(["sf", "data", "query", "--target-org", "de", "--query", QUERY, "--json"], cwd=work, env=env,
                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
began, appeared, shown = time.time(), None, None
while time.time() - began < 45 and appeared is None:
    if pids("SecurityAgent", exact=True) or pids(WRITER):
        appeared = round(time.time() - began, 1)
    elif proc.poll() is not None:
        break
    else:
        time.sleep(0.5)
if appeared is not None:
    sampled = time.time()
    while time.time() - sampled < 12 and shown is None:
        snap = snapshot()
        on = [w for w in snap["agent_windows"] if w.get("onscreen")]
        if on:
            shown = (round(time.time() - began, 1), on)
        else:
            time.sleep(0.4)
agent = pids("SecurityAgent", exact=True)
owner = subprocess.run(["ps", "-o", "user=", "-p", str(agent[0])], capture_output=True, text=True).stdout.strip() if agent else "-"
print(f"  dialog process appeared after {appeared} s (SecurityAgent {agent}, run by {owner}); sf still blocked: {proc.poll() is None}")
print(f"  its window on screen: {shown if shown else 'NOT SEEN by the window list'}")
control_ok = appeared is not None
os.killpg(proc.pid, signal.SIGTERM)
time.sleep(1.5)
survivors = subprocess.run(["pgrep", "-g", str(proc.pid)], capture_output=True, text=True).stdout.split()
if survivors:
    os.killpg(proc.pid, signal.SIGKILL)
proc.communicate()
gone, began = None, time.time()
while time.time() - began < 30:
    if clear(snapshot()):
        gone = round(time.time() - began, 1)
        break
    time.sleep(1)
print(f"  process group killed (survivors after SIGTERM: {len(survivors)}); dialog gone {gone} s later")
if gone is None:
    print(f"  STILL UP: {json.dumps(snapshot())}  <- someone has to click Cancel")

# ---------------------------------------------------------------- fixed: what the trials ran, with the harness's env
print("\n== fixed: the harness's own throwaway-HOME environment, the commands the trials ran")
home, work = fresh_home("fixed")
env = hosts.host("codex").env(home)
print(f"  codex env carries {VAR}={env.get(VAR)}; grok env: ", end="")
try:
    print(hosts.host("grok").env(fresh_home("grokenv")[0]).get(VAR))
except BaseException as exc:  # a host that is not signed in refuses to build its environment
    print(f"not built ({type(exc).__name__})")
commands = [["sf", "--version"],
            ["sf", "alias", "list"],
            ["sf", "data", "query", "--target-org", "de", "--query", QUERY, "--result-format", "human"],
            ["sf", "org", "list", "metadata", "--metadata-type", "CustomTab", "--target-org", "de", "--json"],
            ["sf", "apex", "run", "test", "--target-org", "de", "--class-names", "X", "--synchronous"]]
fixed_ok = True
for argv in commands:
    status, seconds, out = run_to_end(argv, env, work)
    snap = snapshot()
    fixed_ok &= clear(snap) and status != "TIMEOUT"
    print(f"  {' '.join(argv[:4]):<44} {status:<9} {seconds:>5} s  {reason(out):<28} dialog: {show(snap)}")
key = home / ".sfdx" / "key.json"
print(f"  key kept in the throwaway HOME: {key.is_file()} (mode {oct(key.stat().st_mode & 0o777) if key.is_file() else '-'})")
time.sleep(4)
late = snapshot()
fixed_ok &= clear(late)
print(f"  4 s after the last command: {show(late)}")

# ---------------------------------------------------------------- wrapper: the guarded case's sf, real HOME inside
print("\n== wrapper: the guarded case's sf (sf_guard.py) called from the throwaway-HOME environment")
case = json.loads((CHECKOUT / "test/shiploop_e2e/cases.json").read_text())["battleship-salesforce-ui"]["platform"]["model_bin"]
platform = Path(tempfile.mkdtemp(prefix="platform-", dir=SCRATCH))
bins = run.write_model_bin({"sf": case["sf"]}, platform, Path.home())
status, seconds, out = run_to_end([bins["sf"], "org", "list", "--json"], env, work)
try:
    doc = json.loads(out[out.index("{"):])
    orgs = [o for group in (doc.get("result") or {}).values() if isinstance(group, list) for o in group]
    summary = f"{len(orgs)} orgs, alias de: {any(o.get('alias') == 'de' for o in orgs)}"
except ValueError:
    summary = reason(out)
snap = snapshot()
wrapper_ok = status == "exit 0" and clear(snap)
print(f"  wrapper sf org list: {status} in {seconds} s, {summary}; dialog: {show(snap)}")
print(f"  the wrapper script unsets the variable: {'-u ' + VAR in Path(bins['sf']).read_text()}; "
      f"the real HOME has no key file: {not (Path.home() / '.sfdx' / 'key.json').exists()}")

# ---------------------------------------------------------------- chrome, the way the UI check launches it
print("\n== chrome: headless through Playwright with the installed Google Chrome, as the UI check launches it")
modules = glob.glob(str(Path.home() / ".cache/codex-runtimes/*/dependencies/node/node_modules/playwright"))
script = ("const pw=require(process.argv[1]);(async()=>{const b=await pw.chromium.launch({headless:true,"
          "executablePath:process.argv[2]});const p=await b.newPage();await p.setContent('<button>ok</button>');"
          "console.log('chrome',b.version(),await p.textContent('button'));await b.close();})()"
          ".catch(e=>{console.log('FAIL',String(e.message).split('\\n')[0]);process.exit(1)})")
chrome_ok = None
if not modules or not os.path.exists(CHROME):
    print("  Playwright module or Google Chrome not found: skipped")
else:
    chrome_ok = True
    real_env = {k: v for k, v in os.environ.items() if not k.startswith(("NODE_", "PLAYWRIGHT_", "NPM_CONFIG_"))}
    for label, use in (("real HOME", real_env), ("throwaway HOME", env)):
        before = set(pids("Google Chrome", exact=False))
        status, seconds, out = run_to_end(["node", "-e", script, modules[0], CHROME], use, work, timeout=120)
        snap = snapshot()
        last = out.strip().splitlines()[-1] if out.strip() else ""
        launched = last.startswith("chrome ") and last.endswith(" ok")
        chrome_ok &= clear(snap) and launched
        print(f"  {label:<15} {status} in {seconds} s: {last[:90]}; dialog: {show(snap)}")

print("\n== verdict")
print(f"  control raised the dialog, so the check can see one: {control_ok}; its window seen on screen: {shown is not None}")
print(f"  fixed environment raised none: {fixed_ok}")
print(f"  guarded wrapper works and raised none: {wrapper_ok}")
print(f"  Chrome launched and raised none: {chrome_ok}")
sys.exit(0 if (control_ok and fixed_ok and wrapper_ok and chrome_ok) else 1)
