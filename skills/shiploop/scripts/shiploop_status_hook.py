#!/usr/bin/env python3
"""Claude Code PostToolUse adapter: show ShipLoop's own status to the user.

Reads the hook payload on stdin. When the Bash call was a direct ShipLoop CLI
invocation whose stdout carries the script-rendered status block, prints
``{"systemMessage": <two-line compact status>}``; otherwise prints nothing. It never reads run
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

import shiploop_prompts as guidance  # noqa: E402

BEGIN = "=== ShipLoop status ==="
END = "=== end ShipLoop status ==="
# The Claude Code terminal CLI keeps a hook message's own SGR styling (measured
# on 2.1.283); host text in the narrative is already stripped of control codes.
BOLD, PLAIN = "\x1b[1m", "\x1b[22m"
NARRATIVE_BEGIN = "=== ShipLoop narrative ==="
NARRATIVE_END = "=== end ShipLoop narrative ==="
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
    guidance.inner_context(route, improve=improve)
    for route in guidance.DELEGATIONS
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


# Payload shapes whose after-shell hook output can reach the user.  Claude Code
# and Codex share one shape; of their surfaces only the Claude Code terminal CLI
# displays the message (the desktop app, the VS Code panel and the Codex 0.157.1
# TUI drop it), which is why the packet itself routes the narrative to the owner
# everywhere else.  Grok never shows a successful PostToolUse hook's output and
# Cursor's afterShellExecution has no output field.
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


def compact(block: str) -> str:
    """Two lines from the block: where the run is, then what finished and what comes next.

    Hosts show a hook message as a warning, so the full block reads as an alarm
    at every step; ``status`` and ``status.md`` keep the full block.
    """
    rows: dict[str, str] = {}
    for row in block.splitlines()[1:-1]:
        label, sep, value = row.partition(":")
        if sep:
            rows.setdefault(label.strip(), value.strip())
    if not rows.get("Where"):
        return block
    second = [f"Done: {rows['Done']}"] if rows.get("Done") else []
    for label in ("Waiting on you", "Stopped", "Next"):
        if rows.get(label):
            second.append(f"{label}: {rows[label]}")
            break
    return "\n".join(["ShipLoop ▶ " + rows["Where"]] + ([" | ".join(second)] if second else []))


def narrative_text(stdout: str) -> str | None:
    """The packet's milestone narrative as plain text, or None when this packet has none."""
    head = stdout[:WINDOW]
    start, end = head.find(NARRATIVE_BEGIN), head.find(NARRATIVE_END)
    if start < 0 or end < start or head.count(NARRATIVE_BEGIN) != 1:
        return None
    # Skip the begin marker and the owner's instruction line; keep the Markdown body.
    body = head[start:end].split("\n", 2)[2:]
    if not body:
        return None
    lines = []
    for line in body[0].strip().splitlines():
        if line.startswith("#"):
            line = BOLD + line.lstrip("#").strip().replace("**", "") + PLAIN
        else:
            # Markdown bold becomes terminal bold; code spans lose their backticks.
            parts = line.replace("`", "").split("**")
            line = "".join(part if index % 2 == 0 else BOLD + part + PLAIN
                           for index, part in enumerate(parts))
        lines.append(line)
    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text) or None


def status_message(payload: Any) -> str | None:
    """Return what to show the user, only on hosts that can display it.

    A milestone packet carries the run narrative; every other packet shows the
    compact two-line status.
    """
    found = status_block(payload)
    if found is None or found[0] not in DISPLAY_HOSTS:
        return None
    call = shell_call(payload)
    story = narrative_text(call[2]) if call is not None else None
    return story or compact(found[1])


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
