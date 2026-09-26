#!/usr/bin/env python3
"""Claude Code PostToolUse adapter: show ShipLoop's own status block to the user.

Reads the hook payload on stdin. When the Bash call was a direct ShipLoop CLI
invocation whose stdout carries the script-rendered status block, prints
``{"systemMessage": <block>}``; otherwise prints nothing. It never reads run
state, resolves paths, or fails the tool call: every problem exits 0 silently.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shiploop_navigator_v3_prompts as guidance3  # noqa: E402

BEGIN = "=== ShipLoop status ==="
END = "=== end ShipLoop status ==="
HEADER = "ShipLoop navigator | "
# The block must end this early in stdout; Claude Code keeps only the head of
# oversized Bash output, and the block sits right after the callback line.
WINDOW = 8000
ENTRY_POINTS = {"shiploop": None, "shiploop-complete": "complete", "shiploop-next": "next"}
WRAPPER_LINES = {
    "complete": "shiploop complete — close the increment and print the next stdout\n",
    "next": "shiploop next — reprint stdout\n",
}
PACKET_VERBS = {
    "init", "next", "context", "complete", "improve-bind", "improve-complete",
    "improve-reconcile", "pause", "resume", "halt", "delegation", "lint-mode",
}
INTERPRETER = re.compile(r"python(\d+(\.\d+)*)?$")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
PREFIXES = {
    guidance3.inner_context(route, improve=improve)
    for route in guidance3.DELEGATIONS
    for improve in (False, True)
}


def _verb(command: str) -> tuple[str, str | None] | None:
    """Return (verb, wrapper) for one direct ShipLoop CLI call, else None."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    # Pipes, redirects, chains and backgrounding change or split the stdout.
    if any(token and set(token) <= set("|&;<>()") for token in tokens):
        return None
    for index, token in enumerate(tokens):
        name = os.path.basename(token)
        parent = os.path.basename(os.path.dirname(token))
        if name in ENTRY_POINTS and parent == "scripts":
            break
        if not (INTERPRETER.match(os.path.basename(token)) or ASSIGNMENT.match(token)
                or token in ("env", "exec")):
            return None
    else:
        return None
    wrapper = ENTRY_POINTS[name]
    rest = tokens[index + 1:]
    if wrapper is not None:
        return wrapper, wrapper
    if not rest:
        return None
    if rest[0] == "workspace":
        return ("init", None) if rest[1:2] == ["start"] else None
    if rest[0] == "status" or rest[0] in PACKET_VERBS:
        return rest[0], None
    return None


def _output(response: Any, *keys: str) -> str | None:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in keys:
            value = response.get(key)
            if isinstance(value, str):
                return value
            # Grok sends a shell command's raw output as a list of byte values.
            if isinstance(value, list) and value and all(isinstance(b, int) and 0 <= b < 256 for b in value):
                return bytes(value).decode("utf-8", "replace")
    return None


# Hosts whose after-shell hook output can reach the user.  Grok never shows a
# successful PostToolUse hook's output and Cursor's afterShellExecution has no
# output field, so there the in-packet block remains the display.
DISPLAY_HOSTS = {"claude-or-codex"}


def shell_call(payload: Any) -> tuple[str, str, str] | None:
    """Return (host, command, output) from a host's after-shell hook payload."""
    if not isinstance(payload, dict):
        return None
    # Grok also sends snake_case aliases (tool_name, tool_response), so its
    # camelCase keys are checked before the Claude/Codex shape.
    if "toolName" in payload:  # Grok.
        tool_input = payload.get("toolInput")
        if payload.get("toolName") not in ("run_terminal_command", "Bash") or not isinstance(tool_input, dict):
            return None
        host, command = "grok", tool_input.get("command")
        output = _output(payload.get("toolResult", payload.get("tool_response")),
                         "output", "output_for_prompt", "stdout")
    elif "tool_name" in payload:  # Claude Code and Codex share this shape.
        tool_input = payload.get("tool_input")
        if payload.get("tool_name") != "Bash" or not isinstance(tool_input, dict):
            return None
        host, command = "claude-or-codex", tool_input.get("command")
        output = _output(payload.get("tool_response"), "stdout", "output")
    elif "command" in payload and "output" in payload:  # Cursor afterShellExecution.
        host, command, output = "cursor", payload.get("command"), _output(payload.get("output"))
    else:
        return None
    if not isinstance(command, str) or not output:
        return None
    return host, command, output


def status_block(payload: Any) -> tuple[str, str] | None:
    """Return (host, block) when this call was a direct ShipLoop call carrying its block."""
    call = shell_call(payload)
    if call is None:
        return None
    host, command, stdout = call
    found = _verb(command)
    if found is None:
        return None
    verb, wrapper = found
    if wrapper is not None:
        line = WRAPPER_LINES[wrapper]
        if not stdout.startswith(line):
            return None
        stdout = stdout[len(line):]
    if verb == "status":
        if not stdout.startswith(BEGIN):
            return None
    else:
        body = stdout
        for prefix in PREFIXES:
            if body.startswith(prefix):
                body = body[len(prefix):].lstrip("\n")
                break
        if not body.startswith(HEADER):
            return None
    head = stdout[:WINDOW]
    start, end = head.find(BEGIN), head.find(END)
    if start < 0 or end < start or head.count(BEGIN) != 1:
        return None
    return host, head[start:end + len(END)]


def status_message(payload: Any) -> str | None:
    """Return the block to show the user, only on hosts that can display it."""
    found = status_block(payload)
    return found[1] if found is not None and found[0] in DISPLAY_HOSTS else None


def main() -> int:
    try:
        message = status_message(json.load(sys.stdin))
        if message is not None:
            print(json.dumps({"systemMessage": message}))
    except Exception:  # noqa: BLE001 - a display hook must never fail the tool call
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
