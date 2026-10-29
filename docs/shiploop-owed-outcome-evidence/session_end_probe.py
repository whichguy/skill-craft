"""Does Claude Code run a SessionEnd hook when a session ends, and with what payload? Does a signal run it mid-turn?

Starts headless Claude Code sessions (the E2E harness's Ollama route, so no Anthropic login is sent) in a throwaway
project whose settings register a SessionEnd hook that saves its stdin. The keepalive's session-end hook releases the
run a session owned from that payload, so the fields it needs (session_id, and no subagent keys) must be there.

Modes, each one fresh session, run in this order:
  graceful       the session ends by itself after one short turn (the first probe, 2026-10-28)
  SIGTERM, SIGINT, SIGHUP, SIGKILL
                 the session is mid-turn (a Bash `sleep` is running, shown by a PreToolUse hook) when that signal goes to
                 the host's process alone; what the harness's slice would send to end a cleared session
  wrapped:SIGTERM, wrapped:SIGINT
                 the same, with the host under `caffeinate -d -i`, as run.launch starts it, and the signal sent to the
                 leader, which is caffeinate: does the signal reach the host through it?

Per mode it records whether SessionEnd fired, with its payload, how long after the signal, the exit status and whether the
host had exited. The route's isolation is the harness's own (hosts.ClaudeHost.env scrubs the ANTHROPIC_* and CLAUDE*
environment and routes to Ollama); the probe checks the scrub and refuses to start a session if a variable of those
families other than the route's own is in the environment it would pass.

    python3 docs/shiploop-owed-outcome-evidence/session_end_probe.py [--model MODEL] [--modes graceful,SIGTERM,...]
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts
import listeners
import run

MODES = ("graceful", "SIGTERM", "SIGINT", "SIGHUP", "SIGKILL", "wrapped:SIGTERM", "wrapped:SIGINT")
MID_TURN_PROMPT = ("Run this exact shell command with the Bash tool and wait for it to finish, then reply with the single "
                   "word done: sleep 120")
GRACEFUL_PROMPT = "Reply with the single word ok."
HOOK_TIMEOUT = 10  # seconds, as the keepalive registers its SessionEnd hook (shiploop_keepalive._claude_style_entries)
TOOL_WAIT = 180  # seconds to wait for the model to start the sleep
EXIT_WAIT = 30  # seconds the host gets to end after the signal, past the hook's own timeout
ATTEMPTS = 3  # a model that answers without running the command (no turn in flight) gets the mode again


def route_env(host, home: Path) -> dict:
    """The environment a session gets: the harness's scrubbed Ollama route; refused if it still carries a login."""
    env = host.env(home)
    own = {"ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", *hosts.OLLAMA_MODEL_VARS}
    stray = sorted(name for name in env if name.startswith(hosts.OLLAMA_SCRUB_PREFIXES) and name not in own)
    if stray:
        raise SystemExit(f"refusing to start a session: the environment still carries {stray}")
    return env


def write_project(work: Path) -> dict:
    """A throwaway project whose SessionEnd and PreToolUse hooks append {hook, at, payload} to one file each."""
    hook = work / "hook.py"
    hook.write_text("import json, sys, time\n"
                    "name = sys.argv[1]\n"
                    "with open(sys.argv[2] + '/' + name + '.jsonl', 'a') as f:\n"
                    "    f.write(json.dumps({'hook': name, 'at': time.time(), 'payload': json.loads(sys.stdin.read() or '{}')}) + '\\n')\n")
    (work / ".claude").mkdir()
    command = lambda name: f"{sys.executable} {hook} {name} {work}"
    (work / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "SessionEnd": [{"hooks": [{"type": "command", "command": command("session-end"), "timeout": HOOK_TIMEOUT}]}],
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command("pre-tool")}]}]}}))
    return {"session-end": work / "session-end.jsonl", "pre-tool": work / "pre-tool.jsonl"}


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []


def probe(host, mode: str, model: str) -> dict:
    wrapped, _, name = mode.rpartition(":")
    work = Path(tempfile.mkdtemp(prefix="session-end-probe-"))
    files = write_project(work)
    prompt = GRACEFUL_PROMPT if name == "graceful" else MID_TURN_PROMPT
    argv = host.argv(prompt=prompt, prompt_file=None, cwd=work, model=model, effort=None, permission_mode="auto",
                     max_turns=3)
    if wrapped:
        argv = run.keep_awake(argv)
    env = route_env(host, work / "home")
    started = time.time()
    with (work / "stdout.jsonl").open("wb") as out, (work / "stderr.txt").open("wb") as err:
        proc = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                start_new_session=True)
        sent = None
        try:
            if name != "graceful":
                while not rows(files["pre-tool"]) and listeners.unreaped(proc.pid) == "running":
                    if time.time() - started > TOOL_WAIT:
                        break
                    time.sleep(0.5)
                if rows(files["pre-tool"]):
                    time.sleep(2)  # the sleep is running
                    if listeners.unreaped(proc.pid) == "running":
                        sent = time.time()
                        os.kill(proc.pid, getattr(signal, name))
            deadline = time.time() + (EXIT_WAIT if sent else 300)
            while listeners.unreaped(proc.pid) == "running" and time.time() < deadline:
                time.sleep(0.25)
            exited_at = time.time() if listeners.unreaped(proc.pid) != "running" else None
            alive_at_deadline = listeners.unreaped(proc.pid) == "running"
            left = [row["command"][:80] for row in run.lifecycle.table().values()
                    if row["pgid"] == proc.pid and row["pid"] != proc.pid]
            listeners.end_group(proc.pid)  # only the group this probe started, while its leader is unreaped
            proc.wait()
        finally:
            if proc.poll() is None:
                listeners.end_group(proc.pid)
                proc.wait()
    ended = rows(files["session-end"])
    status = proc.returncode
    return {"mode": mode, "signal_sent": name if sent else None, "turn_in_flight": bool(rows(files["pre-tool"])),
            "host_exited_by_itself": not alive_at_deadline,
            "exit": f"signal {-status}" if status is not None and status < 0 else status,
            "seconds_from_signal_to_exit": round(exited_at - sent, 1) if sent and exited_at else None,
            "left_in_group_when_leader_exited": left,
            "session_end_fired": bool(ended),
            "seconds_from_signal_to_session_end": round(ended[0]["at"] - sent, 1) if ended and sent else None,
            "session_end_payloads": [row["payload"] for row in ended],
            "has_session_id": bool(ended) and all(row["payload"].get("session_id") for row in ended)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4.1-flash:1017-cloud")
    parser.add_argument("--modes", default=",".join(MODES), help=f"comma-separated, from: {', '.join(MODES)}")
    args = parser.parse_args()
    modes = args.modes.split(",")
    if unknown := [mode for mode in modes if mode not in MODES]:
        raise SystemExit(f"unknown mode {unknown}; the modes are {', '.join(MODES)}")
    host = hosts.host("claude", None, "ollama")
    host.model = args.model
    if why := hosts.ollama_ready(args.model):
        raise SystemExit(f"Ollama is not ready: {why}")
    results = []
    for mode in modes:
        for attempt in range(1, ATTEMPTS + 1):
            result = probe(host, mode, args.model)
            if result["turn_in_flight"] or mode == "graceful":
                break
        results.append({**result, "attempts": attempt})
    print(json.dumps({"model": args.model, "hook_timeout_seconds": HOOK_TIMEOUT, "results": results}, indent=1))
    return 0 if all(r["session_end_fired"] and r["has_session_id"] for r in results if r["mode"] == "graceful") else 1


if __name__ == "__main__":
    sys.exit(main())
