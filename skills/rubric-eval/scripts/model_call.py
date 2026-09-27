"""model_call: one isolated headless model call on any supported host, behind one interface.

A model is named by a spec, "host:model@effort" (effort optional), or by a short alias:

    grok    grok:grok-4.7@medium
    opus    claude:claude-opus-5-5@medium
    sonnet  claude:sonnet
    luna    codex:gpt-5.6-luna@xhigh

`call_full(spec, prompt, tools=..., workspace=...)` returns the same record for every host:
    {"text", "input_tokens", "output_tokens", "seconds", "outside": [...] or None, "spec": resolved spec}
Tokens count cached and uncached input once, and output with reasoning; None when the host did not report
them. "outside" lists what the call touched beyond its own directory (paths, or "tool:<name>" for a tool
outside the read-only allowlist), from the host's own record of the call; None when it cannot be audited.

Every call runs from its own fresh temporary directory, with no MCP servers, plugins or user configuration.
tools="" asks for no tools; tools="Read" allows reading, listing and searching only (never writes, never
auto-approval). No host here can fence reads to the directory on this machine, so reads are audited instead:
a caller should discard a call whose "outside" is non-empty (rubric-eval's `run` does).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ALIASES = {
    "grok": "grok:grok-4.7@medium",
    "opus": "claude:claude-opus-5-5@medium",
    "sonnet": "claude:sonnet",
    "luna": "codex:gpt-5.6-luna@xhigh",
}
HOSTS = ("grok", "claude", "codex")
NO_MCP = ["--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
PATH_KEYS = ("target_file", "target_directory", "path", "file_path")
GROK_READ_TOOLS = ("read_file", "list_dir", "grep")
CLAUDE_READ_TOOLS = ("Read", "Grep", "Glob")


def resolve(spec: str) -> dict:
    """{"host", "model", "effort", "spec"} for an alias or a host:model@effort spec."""
    full = ALIASES.get(spec, spec)
    m = re.fullmatch(r"(\w+):([\w.\-]+)(?:@(\w+))?", full)
    if not m or m.group(1) not in HOSTS:
        raise ValueError(f"model_call: unknown model {spec!r}; use an alias {sorted(ALIASES)} or host:model@effort "
                         f"with host in {HOSTS}")
    return {"host": m.group(1), "model": m.group(2), "effort": m.group(3), "spec": full}


def _outside(path: str, root: str) -> bool:
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    return full != root and not full.startswith(root + os.sep)


# ---------------------------------------------------------------- grok

def grok_home() -> Path:
    """An isolated Grok home holding only the sign-in, so no plugins, skills or MCP servers load."""
    home = Path(os.environ.get("RUBRIC_EVAL_GROK_HOME") or Path(tempfile.gettempdir()) / "rubric-eval-grok-home")
    auth = Path.home() / ".grok" / "auth.json"
    (home / ".grok").mkdir(parents=True, exist_ok=True)
    link = home / ".grok" / "auth.json"
    if not link.exists():
        if not auth.is_file():
            raise SystemExit(f"model_call: Grok is not signed in ({auth} is missing)")
        link.symlink_to(auth)
    return home


def grok_outside(home: Path, session_id: str, cwd: str) -> list[str] | None:
    """What a Grok session touched beyond `cwd`, from its session log (None if the log is missing)."""
    logs = list((home / ".grok" / "sessions").glob(f"*/{session_id}/updates.jsonl"))
    if not logs:
        return None
    root = os.path.realpath(cwd); seen = set()
    for line in logs[0].read_text(errors="replace").splitlines():
        try:
            u = json.loads(line)["params"]["update"]
        except (ValueError, KeyError, TypeError):
            continue
        if u.get("sessionUpdate") != "tool_call":
            continue
        if u.get("title") not in GROK_READ_TOOLS:
            seen.add(f"tool:{u.get('title')}")
        for k in PATH_KEYS:
            v = (u.get("rawInput") or {}).get(k)
            if isinstance(v, str) and v and _outside(v, root):
                seen.add(v)
    return sorted(seen)


def _grok(m: dict, prompt: str, cwd: str, tools: str, timeout: int, rec: dict) -> None:
    home = grok_home()
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GROK_CONFIG_DIR": str(home / ".grok"),
           "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
           "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
           "GROK_CLAUDE_SKILLS_ENABLED": "false", "GROK_CURSOR_SKILLS_ENABLED": "false", "NO_COLOR": "1"}
    # Grok reads `--tools ""` as no restriction (shell included), so always name an allowlist; todo_write
    # touches no files. The prompt goes inline (-p), so no prompt file is on disk for another call to find.
    argv = ["grok", "--cwd", cwd, "-p", prompt, "--verbatim", "--model", m["model"], "--output-format", "json",
            "--no-auto-update", "--disable-web-search", "--disallowed-tools", "search_tool,use_tool"]
    argv += ["--reasoning-effort", m["effort"]] if m["effort"] else []
    argv += ["--tools", ",".join(GROK_READ_TOOLS), "--max-turns", "40"] if tools else ["--tools", "todo_write", "--max-turns", "6"]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL).stdout
    d = json.loads(out) if out.strip() else {}
    rec["text"] = d.get("text", "")
    u = d.get("usage")
    if isinstance(u, dict) and "input_tokens" in u and "output_tokens" in u:
        # input_tokens excludes cache reads (total = input + cache read + output); output includes reasoning
        rec.update(input_tokens=u["input_tokens"] + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                   output_tokens=u["output_tokens"])
    if d.get("sessionId"):
        rec["outside"] = grok_outside(home, d["sessionId"], cwd)


# ---------------------------------------------------------------- claude

def claude_outside(events: list[dict], cwd: str) -> list[str]:
    """What a Claude session touched beyond `cwd`, from its stream-json tool_use blocks."""
    root = os.path.realpath(cwd); seen = set()
    for e in events:
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") not in CLAUDE_READ_TOOLS:
                seen.add(f"tool:{b.get('name')}")
            for k in ("file_path", "path"):
                v = (b.get("input") or {}).get(k)
                if isinstance(v, str) and v and _outside(v, root):
                    seen.add(v)
    return sorted(seen)


def _claude(m: dict, prompt: str, cwd: str, tools: str, timeout: int, rec: dict) -> None:
    allowed = ",".join(CLAUDE_READ_TOOLS) if tools else ""
    argv = ["claude", "-p", "--model", m["model"], "--output-format", "stream-json", "--verbose",
            "--tools", allowed, *NO_MCP] + (["--effort", m["effort"]] if m["effort"] else []) + (["--allowedTools", allowed] if tools else [])
    out = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=cwd).stdout
    events = []
    for line in out.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    rec["text"] = final.get("result", "") if not final.get("is_error") else ""
    u = final.get("usage")
    if isinstance(u, dict) and "input_tokens" in u and "output_tokens" in u:  # input_tokens excludes cache
        rec.update(input_tokens=u["input_tokens"] + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
                   output_tokens=u["output_tokens"])
    rec["outside"] = claude_outside(events, cwd)


# ---------------------------------------------------------------- codex

SYSTEM_PREFIXES = ("/bin/", "/usr/", "/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/opt/homebrew/bin/")


def codex_outside(events: list[dict], cwd: str) -> list[str]:
    """What a Codex session touched beyond `cwd`: path-like words in the shell commands it ran (best effort:
    absolute paths outside cwd, `..` escapes, `~` and $HOME), from its --json events. Codex always has a shell."""
    root = os.path.realpath(cwd); seen = set()
    for e in events:
        it = e.get("item") or {}
        if e.get("type") != "item.completed" or it.get("type") != "command_execution":
            continue
        cmd = it.get("command") or ""
        try:
            words = shlex.split(cmd)
            if len(words) >= 3 and words[1] in ("-lc", "-c"):  # /bin/zsh -lc "<inner>"
                words = shlex.split(words[2])
        except ValueError:
            words = cmd.split()
        for w in words:
            for part in re.split(r"[=:,]", w):
                if part.startswith(("~", "$HOME", "${HOME}")):
                    seen.add(part)
                elif part.startswith("/") and not part.startswith(SYSTEM_PREFIXES) and _outside(part, root):
                    seen.add(part)
                elif ".." in part.split("/") and _outside(part, root):
                    seen.add(part)
    return sorted(seen)


def _codex(m: dict, prompt: str, cwd: str, tools: str, timeout: int, rec: dict) -> None:
    # --ignore-user-config: no MCP servers or profiles from ~/.codex/config.toml (auth still loads).
    # read-only sandbox: no writes. Codex reads through its shell, which cannot be removed; with tools="" the
    # prompt still reaches a model that could run commands, so both modes are audited the same way.
    argv = ["codex", "exec", "--ignore-user-config", "--skip-git-repo-check", "-m", m["model"], "-s", "read-only",
            "-C", cwd, "--json"] + (["-c", f'model_reasoning_effort="{m["effort"]}"'] if m["effort"] else []) + [prompt]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL).stdout
    events = []
    for line in out.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    msgs = [e["item"].get("text", "") for e in events
            if e.get("type") == "item.completed" and (e.get("item") or {}).get("type") == "agent_message"]
    rec["text"] = msgs[-1] if msgs else ""
    turns = [e.get("usage") for e in events if e.get("type") == "turn.completed" and isinstance(e.get("usage"), dict)]
    if turns:  # OpenAI usage: cached input is part of input_tokens; reasoning is part of output_tokens
        rec.update(input_tokens=sum(u.get("input_tokens", 0) for u in turns), output_tokens=sum(u.get("output_tokens", 0) for u in turns))
    rec["outside"] = codex_outside(events, cwd)


# ---------------------------------------------------------------- entry points

def call_full(spec: str, prompt: str, *, timeout: int = 600, tools: str = "", workspace: str | Path | None = None) -> dict:
    """One isolated call; see the module docstring for the record it returns. Never raises on a failed call:
    text is '' and the caller treats it as a stub."""
    if tools not in ("", "Read"):
        raise ValueError(f"call: tools must be '' or 'Read', got {tools!r}")
    m = resolve(spec)
    rec = {"text": "", "input_tokens": None, "output_tokens": None, "seconds": 0.0, "outside": None, "spec": m["spec"]}
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="rubric-eval-") as cwd:
        if workspace:
            shutil.copytree(workspace, cwd, dirs_exist_ok=True)
        try:
            {"grok": _grok, "claude": _claude, "codex": _codex}[m["host"]](m, prompt, cwd, tools, timeout, rec)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
    rec["seconds"] = round(time.monotonic() - start, 1)
    return rec


def call(spec: str, prompt: str, *, timeout: int = 600, tools: str = "") -> str:
    """The text of one isolated call ('' on failure); see call_full for usage, time and the audit."""
    return call_full(spec, prompt, timeout=timeout, tools=tools)["text"]
