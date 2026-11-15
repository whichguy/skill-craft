#!/usr/bin/env python3
"""The Grok PreToolUse hook the E2E harness installs in a Grok run's throwaway profile: it refuses in the turn a shell
command that Grok's headless Auto-review would refuse by ending the session.

Grok's Auto-review (``--permission-mode auto``) checks which files a shell command writes before its classifier reviews
the command. When it cannot resolve a written path it needs a person to approve the call. A headless run has none, so
Grok refuses the call, ends the turn as cancelled and skips the Stop hook, and the harness has to start the session
again (docs/experiments/grok-headless-refusals-20261115). This hook denies those commands first, with a reason the model
reads, so the turn goes on and the model rewrites the command. It never approves, rewrites or delays a call: any other
command, any other tool and any failure of its own get no opinion, and Grok's own checks decide as before.

The shapes are the ones the 2026-11-15 probes found on Grok 1.0.77 (``CALIBRATED_BUILD``), each refused in 0 to 13 ms
without a classifier call:

- a write target of ``mkdir``, ``touch`` or ``rm`` (every operand), of ``cp``, ``mv`` or ``ln`` (the destination), or of
  ``tee`` (every file) that holds a shell expansion (``$VAR``, ``${...}``, ``$(...)``), even when the variable was set to a
  literal path a line before (``var-write``);
- such a target, or a shell redirect's target, that is relative after a ``cd`` or ``pushd`` to a folder other than the
  session's own (``cd-relative-write``);
- two adjacent backticks inside a double-quoted word, an empty command substitution, as in a ```` ``` ```` fence of a
  ``python3 -c`` regex (``backtick-in-dq``).

Grok allows the rest of what the probes tried: a redirect to ``"$X/file"``, ``rsync`` and ``tar -C`` into ``"$X"``, a
variable only in a ``cp`` source, reads through variables, ``$(...)`` around a real command, a ``cd`` to the session's own
folder. A shape a later build adds is not caught here; the resume prompt names that refusal instead (run.py).

As a hook, the module reads the PreToolUse event on standard input and prints its decision. ``install`` copies this file
into a profile and registers it; ``denials`` reads back what it denied in a run.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
from pathlib import Path

CALIBRATED_BUILD = "1.0.77"
NAME = "refusal-preempt"  # the hook's files in the profile: hooks/<NAME>.json and hooks/<NAME>.py
SHELL_TOOL = "run_terminal_command"
HOOK_TIMEOUT_SECONDS = 10
# The opening of every deny reason, which run.py counts by: never the word "cancelled" (metrics.cancelled_update would
# read the update as a Grok refusal) and never a phrase of Grok's own refusal text.
MARK = "Not run: Grok's headless permission check would refuse this command"
SHAPE_WORDS = {
    "var-write": "a path it writes holds a shell expansion",
    "cd-relative-write": "a relative path is written after a cd",
    "backtick-in-dq": "two backticks are next to each other inside double quotes",
}
REWRITE = ("Rewrite it so that every file it writes is named by a literal absolute path: no $VAR, ${...} or $(...) in "
           "what mkdir, touch, rm, cp, mv, ln or tee writes; no relative write after a cd (use git -C and absolute paths "
           "instead); and no two backticks together inside double quotes (put Python that reads a ``` block in a script "
           "file). Or write the script to a file with your file tool and run it with one plain command.")

ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
EVERY_OPERAND = frozenset(("mkdir", "touch", "rm", "tee"))
DESTINATION = frozenset(("cp", "mv", "ln"))
OPTION_VALUES = {"mkdir": ("-m", "--mode"), "cp": ("-t", "--target-directory"), "mv": ("-t", "--target-directory"),
                 "ln": ("-t", "--target-directory")}
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")  # not a <<< here-string


def split_heredocs(command: str) -> tuple[str, list[str]]:
    """(the command without its here-document bodies, the bodies of unquoted here-documents). A quoted body (<<'EOF') is
    literal text to the shell; an unquoted one expands like a double-quoted word."""
    lines, kept, expanding, index = command.split("\n"), [], [], 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        index += 1
        for quote, tag in HEREDOC.findall(line):
            body = []
            while index < len(lines) and lines[index].strip() != tag:
                body.append(lines[index])
                index += 1
            index += 1  # the closing tag
            if not quote:
                expanding.append("\n".join(body))
    return "\n".join(kept), expanding


def segments(command: str) -> list[str]:
    """The simple commands of ``command``: split on unquoted newlines, ;, &, | and the ( ) { } of a group."""
    parts, current, quote, index = [], [], None, 0
    while index < len(command):
        char = command[index]
        if quote:
            current.append(char)
            if char == "\\" and quote == '"' and index + 1 < len(command):
                current.append(command[index + 1])
                index += 1
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
            current.append(char)
        elif char == "\\" and index + 1 < len(command):
            current.append(command[index:index + 2])
            index += 1
        elif char in "\n;|&(){}":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def words(segment: str) -> list[str]:
    """The words of one simple command, quotes kept, split on unquoted white space; redirects are left out."""
    found, current, quote, index = [], [], None, 0
    while index < len(segment):
        char = segment[index]
        if quote:
            current.append(char)
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
            current.append(char)
        elif char == "\\" and index + 1 < len(segment):
            current.append(segment[index:index + 2])
            index += 1
        elif char.isspace():
            if current:
                found.append("".join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        found.append("".join(current))
    kept, skip = [], False
    for word in found:
        if skip:
            skip = False
        elif re.fullmatch(r"[0-9]*>>?|[0-9]*<|&>", word):
            skip = True  # the redirect's target follows as its own word
        elif not re.match(r"[0-9]*>|[0-9]*<|&>", word):
            kept.append(word)
    return kept


def redirect_targets(segment: str) -> list[str]:
    """The targets of the > and >> redirects written outside quotes (2>&1 and >&2 name no file)."""
    targets, quote, index = [], None, 0
    while index < len(segment):
        char = segment[index]
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == ">" and (index == 0 or segment[index - 1] not in "=<-"):
            following = index + 1
            if following < len(segment) and segment[following] == ">":
                following += 1
            if following < len(segment) and segment[following] == "&":
                index = following + 1
                continue
            match = re.match(r"\"[^\"]*\"|'[^']*'|[^\s;&|)]+", segment[following:].lstrip())
            if match:
                targets.append(match.group(0))
            index = following
            continue
        index += 1
    return targets


def write_targets(program: str, arguments: list[str]) -> list[str]:
    """What ``program`` writes, from its arguments: every operand of mkdir, touch, rm and tee; the destination of cp, mv
    and ln (the last operand, or the value of -t)."""
    values = OPTION_VALUES.get(program, ())
    operands, target_directory, index = [], None, 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in values:
            if argument in ("-t", "--target-directory") and index + 1 < len(arguments):
                target_directory = arguments[index + 1]
            index += 2
            continue
        if argument.startswith("--target-directory="):
            target_directory = argument.split("=", 1)[1]
        elif not argument.startswith("-") or argument == "-":
            operands.append(argument)
        index += 1
    if program in EVERY_OPERAND:
        return operands
    if target_directory is not None:
        return [target_directory]
    return operands[-1:] if len(operands) > 1 else []


def backtick_in_double_quotes(command: str) -> bool:
    """Two adjacent unescaped backticks inside a double-quoted word (an empty command substitution). Grok 1.0.77 refuses
    that and reviews a backtick pair around a real command (``"a `date` b"``) like any other command."""
    quote = None
    for index, char in enumerate(command):
        if quote == "'":
            if char == "'":
                quote = None
        elif quote == '"':
            if char == '"' and command[index - 1] != "\\":
                quote = None
            elif char == "`" and command[index - 1] != "\\" and command[index + 1:index + 2] == "`":
                return True
        elif char in "'\"":
            quote = char
    return False


def floor_shapes(command: str, cwd: str | None = None) -> list[str]:
    """The shapes of ``command`` that Grok 1.0.77's headless Auto-review refuses before its classifier, sorted; an empty
    list for every other command. ``cwd`` is the session's own folder: a cd to it moves nothing."""
    shapes, moved = set(), False
    command, expanding_bodies = split_heredocs(command)
    for segment in segments(command):
        found = words(segment)
        while found and ASSIGN.match(found[0]):
            found = found[1:]  # leading NAME=value assignments
        if not found:
            continue
        program = found[0].rsplit("/", 1)[-1]
        if program in ("cd", "pushd"):
            target = " ".join(found[1:]).strip("'\"").rstrip("/")
            moved = moved or not (cwd and target == cwd.rstrip("/"))
            continue
        targets = write_targets(program, found[1:]) if program in EVERY_OPERAND | DESTINATION else []
        if any("$" in target for target in targets):
            shapes.add("var-write")
        elif moved and any(not target.strip("'\"").startswith("/") for target in targets):
            shapes.add("cd-relative-write")
        if moved and any(not target.strip("'\"").startswith(("/", "$")) for target in redirect_targets(segment)):
            shapes.add("cd-relative-write")
    if backtick_in_double_quotes(command) or any("``" in body for body in expanding_bodies):
        shapes.add("backtick-in-dq")
    return sorted(shapes)


def reason(shapes: list[str]) -> str:
    """The deny reason the model reads: why the command was not run and how to write it so that Grok can check it."""
    why = "; ".join(SHAPE_WORDS[shape] for shape in shapes)
    return (f"{MARK} before it ran, and that refusal would end the session, because it cannot tell which files the "
            f"command writes ({why}). {REWRITE}")


def decide(payload: dict) -> dict | None:
    """The hook's reply to one PreToolUse event: a deny for a floored shell command, else None (no opinion)."""
    if payload.get("toolName") != SHELL_TOOL or payload.get("toolInputTruncated"):
        return None  # a cut command hides its end, so its shapes are unknown: Grok decides
    command = (payload.get("toolInput") or {}).get("command")
    if not isinstance(command, str):
        return None
    shapes = floor_shapes(command, payload.get("workspaceRoot") or payload.get("cwd"))
    return {"decision": "deny", "reason": reason(shapes), "shapes": shapes} if shapes else None


def log_path(environ: dict | None = None) -> Path:
    """Where the hook records its denials: the run's own state folder (XDG_STATE_HOME in a throwaway profile)."""
    environ = os.environ if environ is None else environ
    state = environ.get("XDG_STATE_HOME") or str(Path(environ.get("HOME") or Path.home()) / ".local" / "state")
    return Path(state) / "shiploop-e2e" / f"{NAME}.jsonl"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        decision = decide(payload) if isinstance(payload, dict) else None
        if decision is None:
            return 0
        command = (payload.get("toolInput") or {}).get("command") or ""
        try:
            path = log_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as handle:
                handle.write(json.dumps({"at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                                         "session": payload.get("sessionId"), "shapes": decision["shapes"],
                                         "command": command[:300]}) + "\n")
        except OSError:
            pass  # a denial that cannot be logged is still a denial
        print(json.dumps({"decision": "deny", "reason": decision["reason"]}))
    except Exception:  # noqa: BLE001 - a broken hook must never block a call: no opinion
        return 0
    return 0


def installed(grok_dir: Path) -> dict | None:
    """The record of the hook a profile already holds (``kept``: it was there before this launch), or None for a profile
    without it. Reads only: a regrade, which starts no host, reports what the run had and writes nothing into it."""
    hooks = Path(grok_dir) / "hooks"
    script, config = hooks / f"{NAME}.py", hooks / f"{NAME}.json"
    if not (script.is_file() and config.is_file()):
        return None
    return {"installed": True, "kept": True, "script": str(script),
            "sha256": hashlib.sha256(script.read_bytes()).hexdigest(), "calibrated_on": CALIBRATED_BUILD}


def install(grok_dir: Path) -> dict:
    """Copy this module into ``grok_dir``/hooks and register it as a PreToolUse hook on Grok's shell tool, before the
    session starts (headless Grok reads its global hooks only then). A profile that already has the hook keeps it, so a
    resumed run keeps the hook it started with; ``kept`` False on a resumed run says the hook arrived at that resume.
    Returns the record result.json keeps."""
    record = installed(grok_dir)
    if record is not None:
        return record
    hooks = Path(grok_dir) / "hooks"
    script, config = hooks / f"{NAME}.py", hooks / f"{NAME}.json"
    hooks.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve(), script)
    config.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": SHELL_TOOL, "hooks": [
        {"type": "command", "command": shlex.join(["python3", str(script)]), "timeout": HOOK_TIMEOUT_SECONDS}]}]}},
        indent=2) + "\n")
    return {**installed(grok_dir), "kept": False}


def denials(home: Path) -> dict:
    """What the hook denied in a run's throwaway profile at ``home``: the count, by shape, and each command's head."""
    path = log_path({"XDG_STATE_HOME": str(Path(home) / ".local" / "state")})
    rows = []
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    shapes: dict = {}
    for row in rows:
        for shape in row.get("shapes") or []:
            shapes[shape] = shapes.get(shape, 0) + 1
    return {"count": len(rows), "shapes": shapes, "commands": [str(row.get("command", ""))[:160] for row in rows]}


if __name__ == "__main__":
    raise SystemExit(main())
