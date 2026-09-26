"""Headless Grok and Claude launches shared by the E2E runner, reviewer and improver.

Grok always runs in a throwaway HOME: its .grok holds only a symlink to the
user's auth.json (plus any plugin installed for the run), so the user's Grok
plugins, the real ~/.grok leader and anything Grok inherits from ~/.claude stay
out, and nothing is installed into the real profile. Claude runs with only
project/local settings, so the user's plugins and hooks stay out.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

# The user's Grok sign-in; the only file an isolated Grok HOME links to.
GROK_AUTH = Path.home() / ".grok" / "auth.json"
HOST_DEFAULTS = {
    "grok": {"model": "grok-4.7", "effort": "medium"},
    "claude": {"model": "sonnet", "effort": None},
}


def grok_env(home: Path, git_config: Path | None = None) -> dict:
    """Create an isolated Grok HOME at `home` and return the environment for it."""
    (home / ".grok").mkdir(parents=True, exist_ok=True)
    if not GROK_AUTH.is_file():
        raise SystemExit(f"Grok is not signed in: {GROK_AUTH} is missing (run grok once to log in)")
    link = home / ".grok" / "auth.json"
    if not link.is_symlink():
        link.symlink_to(GROK_AUTH)
    if git_config is None:
        git_config = home / ".gitconfig"
        git_config.write_text("[user]\n\tname = ShipLoop E2E\n\temail = shiploop-e2e@example.invalid\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "GROK", "XDG_"))}
    env.update(HOME=str(home), GROK_CONFIG_DIR=str(home / ".grok"), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".local/share"), XDG_CACHE_HOME=str(home / ".cache"),
               XDG_STATE_HOME=str(home / ".local/state"),
               GROK_CLAUDE_SKILLS_ENABLED="false", GROK_CURSOR_SKILLS_ENABLED="false",
               GIT_CONFIG_GLOBAL=str(git_config), GIT_TERMINAL_PROMPT="0", NO_COLOR="1")
    return env


def grok_install(env: dict, plugin_dir: Path, grok_bin: str = "grok") -> dict:
    """Install `plugin_dir` into the isolated profile; pass only if it is the one plugin there."""
    install = subprocess.run([grok_bin, "plugin", "install", str(plugin_dir), "--trust"], env=env,
                             capture_output=True, text=True)
    listing = subprocess.run([grok_bin, "plugin", "list"], env=env, capture_output=True, text=True).stdout
    loaded = re.findall(r"^\s*\S+: (\S+) \[local: (.+)\]", listing, re.M)
    wanted = str(plugin_dir.resolve())
    return {"pass": install.returncode == 0 and loaded == [("skill-craft", wanted)],
            "loaded": [f"{name} {path}" for name, path in loaded], "wanted": wanted}


def argv_for(host: str, *, prompt: str, prompt_file: Path, cwd: Path, model: str, effort: str | None,
             permission_mode: str, max_turns: int, max_budget_usd: float = 10.0,
             plugin_dir: Path | None = None, grok_bin: str = "grok", claude_bin: str = "claude") -> list[str]:
    if host == "grok":
        prompt_file.write_text(prompt)
        argv = [grok_bin, "--cwd", str(cwd), "--prompt-file", str(prompt_file), "--verbatim",
                "--output-format", "streaming-json", "--model", model, "--max-turns", str(max_turns),
                "--permission-mode", permission_mode, "--no-auto-update"]
        return argv + (["--reasoning-effort", effort] if effort else [])
    argv = [claude_bin, "-p", prompt, "--model", model, "--max-turns", str(max_turns),
            "--max-budget-usd", str(max_budget_usd), "--permission-mode", permission_mode,
            "--output-format", "stream-json", "--verbose", "--no-session-persistence",
            "--setting-sources", "project,local"]
    if effort:
        argv += ["--effort", effort]
    if plugin_dir is not None:
        argv += ["--plugin-dir", str(plugin_dir.resolve())]
    return argv


def final_text(events_path: Path) -> str:
    """The assistant's closing text: Claude's result, or Grok's text deltas after its last tool call."""
    grok_text, result = "", None
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            result = event["result"]
        elif event.get("type") == "text" and isinstance(event.get("data"), str):
            grok_text += event["data"]
        elif event.get("type") in ("tool_call", "tool_call_update"):
            grok_text = ""
    return result if result is not None else grok_text


def last_json_object(text: str) -> dict | None:
    """The last ```json fenced object in `text`, or the last top-level {...} that parses."""
    fenced = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    candidates = fenced[::-1] or [text[i:] for i in range(len(text)) if text[i] == "{"]
    for candidate in candidates:
        try:
            value, _ = json.JSONDecoder().raw_decode(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def run_agent(argv: list[str], cwd: Path, env: dict, events_path: Path, stderr_path: Path,
              timeout: int) -> dict:
    """Run one headless host process to completion (or kill it at `timeout`)."""
    start = time.time()
    with events_path.open("wb") as out, stderr_path.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                env=env, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
            status = "exited" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            status = "timeout"
    return {"status": status, "returncode": proc.returncode, "elapsed_seconds": round(time.time() - start, 1)}
