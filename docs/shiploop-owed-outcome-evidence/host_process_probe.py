"""Does shiploop_keepalive.host_process() find the host session's own process from inside a real hook?

Starts one headless Claude Code session (the E2E harness's Ollama route, so no Anthropic login is sent) in a throwaway
project whose settings register a PostToolUse(Bash) and a Stop hook. Each hook records what host_process() returns and
the hook's ancestor chain. The answer is right when it names the `claude` process this script started (its pid and start
time), never a hook's launcher and never anything above the session.

    python3 docs/shiploop-owed-outcome-evidence/host_process_probe.py [--model MODEL]
"""
import argparse
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(SCRIPTS))
import hosts
import shiploop_keepalive as keepalive

HOOK = textwrap.dedent('''
    import json, os, sys
    sys.path.insert(0, {scripts!r})
    import shiploop_keepalive as keepalive
    payload = json.load(sys.stdin)
    table, pid, chain = keepalive._processes(), os.getpid(), []
    while pid in table and len(chain) < 8:
        row = table[pid]
        chain.append({{"pid": pid, "name": row["name"], "age": row["age"]}})
        pid = row["ppid"]
    with open({out!r}, "a") as handle:
        handle.write(json.dumps({{"event": payload.get("hook_event_name"), "session": payload.get("session_id"),
                                 "host_process": keepalive.host_process(), "chain": chain}}) + "\\n")
''')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4.1-flash:1017-cloud")
    args = parser.parse_args()
    host = hosts.host("claude", None, "ollama")
    host.model = args.model
    if why := hosts.ollama_ready(args.model):
        raise SystemExit(f"Ollama is not ready: {why}")
    work = Path(tempfile.mkdtemp(prefix="host-process-probe-"))
    out = work / "probe.jsonl"
    hook = work / "hook.py"
    hook.write_text(HOOK.format(scripts=str(SCRIPTS), out=str(out)))
    command = [{"type": "command", "command": f"{sys.executable} {hook}"}]
    (work / ".claude").mkdir()
    (work / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Bash", "hooks": command}], "Stop": [{"hooks": command}]}}))
    argv = host.argv(prompt="Run the shell command `echo probe-ok` once with your Bash tool, then end your turn.",
                     prompt_file=None, cwd=work, model=args.model, effort=None, permission_mode="auto", max_turns=4)
    session = subprocess.Popen(argv, cwd=work, env=host.env(work / "home"), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    started = keepalive._processes().get(session.pid, {}).get("start")
    try:
        session.wait(timeout=300)
    except subprocess.TimeoutExpired:
        session.kill()
    rows = [json.loads(line) for line in out.read_text().splitlines()] if out.is_file() else []
    expected = {"pid": session.pid, "start": started}
    print(json.dumps({"claude": expected, "hooks": rows,
                      "every_hook_found_the_session": bool(rows) and all(r["host_process"] == expected for r in rows)},
                     indent=1))
    return 0 if rows and all(r["host_process"] == expected for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
