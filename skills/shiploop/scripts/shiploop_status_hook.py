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
    guidance3.inner_context(route, stage, improve=improve)
    for route in guidance3.DELEGATIONS
    for stage in guidance3.INNER
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


def _stdout(response: Any) -> str | None:
    if isinstance(response, str):
        return response
    if isinstance(response, dict) and isinstance(response.get("stdout"), str):
        return response["stdout"]
    return None


def status_message(payload: Any) -> str | None:
    """Return the status block to show, or None when this call does not qualify."""
    if not isinstance(payload, dict) or payload.get("tool_name", "Bash") != "Bash":
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    stdout = _stdout(payload.get("tool_response"))
    if not isinstance(command, str) or not stdout:
        return None
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
    return head[start:end + len(END)]


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
