"""Does Claude Code run a SessionEnd hook when a session ends, and with what payload?

Starts one headless Claude Code session (the E2E harness's Ollama route, so no Anthropic login is sent) in a throwaway
project whose settings register a SessionEnd hook that saves its stdin. The keepalive's session-end hook releases the
run a session owned from that payload, so the fields it needs (session_id, and no subagent keys) must be there.

    python3 docs/shiploop-owed-outcome-evidence/session_end_probe.py [--model MODEL]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4.1-flash:1017-cloud")
    args = parser.parse_args()
    host = hosts.host("claude", None, "ollama")
    host.model = args.model
    if why := hosts.ollama_ready(args.model):
        raise SystemExit(f"Ollama is not ready: {why}")
    work = Path(tempfile.mkdtemp(prefix="session-end-probe-"))
    out = work / "session-end.jsonl"
    hook = work / "hook.py"
    hook.write_text(f"import sys\nwith open({str(out)!r}, 'a') as f:\n    f.write(sys.stdin.read().strip() + '\\n')\n")
    (work / ".claude").mkdir()
    (work / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "SessionEnd": [{"hooks": [{"type": "command", "command": f"{sys.executable} {hook}"}]}]}}))
    argv = host.argv(prompt="Reply with the single word ok.", prompt_file=None, cwd=work, model=args.model,
                     effort=None, permission_mode="auto", max_turns=2)
    session = subprocess.run(argv, cwd=work, env=host.env(work / "home"), capture_output=True, text=True, timeout=300,
                             check=False)
    rows = [json.loads(line) for line in out.read_text().splitlines()] if out.is_file() else []
    print(json.dumps({"exit": session.returncode, "session_end_payloads": rows,
                      "fired": bool(rows), "has_session_id": all(r.get("session_id") for r in rows)}, indent=1))
    return 0 if rows and all(r.get("session_id") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
