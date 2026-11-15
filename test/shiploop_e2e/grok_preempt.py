#!/usr/bin/env python3
"""The Grok PreToolUse hook the E2E harness installs in a Grok run's throwaway profile: it refuses in the turn a shell
command that Grok's headless Auto-review would refuse by ending the session.

Grok's Auto-review (``--permission-mode auto``) checks which files a shell command writes before its classifier reviews
the command. When it cannot resolve a written path it needs a person to approve the call. A headless run has none, so
Grok refuses the call, ends the turn as cancelled and skips the Stop hook, and the harness has to start the session
again (docs/experiments/grok-headless-refusals-20261115). This hook denies those commands first, with a reason the model
reads, so the turn goes on and the model rewrites the command. It returns a deny or no opinion: it never approves a call
or replaces its input. Any other command, any other tool, any other permission mode and any failure of its own get no
opinion, and Grok's own checks decide as before.

The rule is the one the 2026-11-15 probes found on Grok 1.0.77 (``CALIBRATED_BUILD``), where each of these is refused in
0 to 13 ms without a classifier call:

- a write target that holds a shell expansion (``$VAR``, ``${...}``, ``$(...)``, a backtick substitution), even when the
  variable was set to a literal path a line before (``var-write``). The targets are every operand of ``mkdir``, ``touch``,
  ``rm`` and ``tee`` (an option's value included: Grok refuses ``touch -r "$X" /f``), and the destination of ``cp``,
  ``mv`` and ``ln`` (the last operand, or the value of a separate ``-t``);
- such a target, or a write redirect's target (``>``, ``>>``, ``>|``, ``&>``), that is relative after a ``cd`` or
  ``pushd`` (``cd-relative-write``). Grok never forgets a ``cd``: not after ``popd``, a return to the session's folder, a
  subshell's end or ``cd .``. Only a ``cd`` to the session's own folder as the command's first step moves nothing;
- an empty command substitution (two backticks, the first opening) inside a double-quoted word or an unquoted
  here-document, as a ```` ``` ```` fence in a ``python3 -c`` regex makes (``backtick-in-dq``).

Grok reads the words as a shell does: a ``$`` in single quotes or after a backslash, and a comment, are literal; a
quoted program name (``"mkdir"``) is the program; ``if``, ``then``, ``do`` and the like, assignments, and the ``env`` and
``timeout`` wrappers (and the other wrappers its guide names) are looked through; a here-string's operand and a
here-document's body are not command words. Grok allows the rest of what the probes tried: a redirect to ``"$X/file"``
(attached or not), ``rsync`` and ``tar -C`` into ``"$X"``, a variable only in a ``cp`` source, ``cp -t"$X"`` (an attached
value), reads through variables, ``$(...)`` around a real command, a backtick pair around a real command. A shape a later
build adds is not caught here; the resume prompt names that refusal instead (run.py). A command the lexer cannot read
to its end (an unterminated quote or substitution) gets no opinion.

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
ACTIVE_MODE = "auto"  # the only permission mode with the floor this hook foresees (the event's permissionMode)
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

ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
EVERY_OPERAND = frozenset(("mkdir", "touch", "rm", "tee"))
DESTINATION = frozenset(("cp", "mv", "ln"))
# Options whose value is the next word and is no operand; touch has none on purpose (Grok refuses `touch -r "$X" /f`).
OPTION_VALUES = {"mkdir": ("-m", "--mode", "--context"), "cp": ("-S", "--suffix"), "mv": ("-S", "--suffix"),
                 "ln": ("-S", "--suffix")}
TARGET_DIRECTORY = ("-t", "--target-directory")
# Words that start a command without being its program (the shell's reserved words).
KEYWORDS = frozenset(("if", "then", "else", "elif", "do", "while", "until", "!", "time", "{"))
WRAPPERS = frozenset(("env", "timeout", "nice", "ionice", "chrt", "stdbuf"))  # Grok's guide peels these
SEPARATORS = (";;", "&&", "||", "|&", ";", "&", "|", "(", ")")
REDIRECTS = ("<<<", "<<-", "<<", "<>", "<&", ">>", ">|", ">&", "<", ">")
WRITE_REDIRECTS = frozenset((">", ">>", ">|", "&>", "&>>"))
NAME_START = re.compile(r"[A-Za-z_]")
NAME_CHARS = re.compile(r"[A-Za-z0-9_]*")


class Unreadable(Exception):
    """The lexer could not read the command to its end: the hook gives no opinion."""


class Word:
    """One shell word: its text after quote removal (expansions kept as written), whether the shell would expand part
    of it, whether any part was quoted or escaped, and its source text."""

    __slots__ = ("text", "expands", "quoted", "raw")

    def __init__(self) -> None:
        self.text, self.expands, self.quoted, self.raw = "", False, False, ""


def _escaped(command: str, index: int) -> bool:
    """Whether command[index] follows an odd run of backslashes."""
    count = 0
    while index - count - 1 >= 0 and command[index - count - 1] == "\\":
        count += 1
    return count % 2 == 1


def _matching_paren(command: str, start: int) -> int:
    """The index after the ``)`` that closes the ``(`` at ``start``, skipping quotes and escapes inside."""
    depth, index = 0, start
    while index < len(command):
        char = command[index]
        if char == "\\":
            index += 2
            continue
        if char == "'":
            end = command.find("'", index + 1)
            if end < 0:
                raise Unreadable
            index = end + 1
            continue
        if char == '"':
            index = _end_of_double_quotes(command, index + 1)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise Unreadable


def _end_of_double_quotes(command: str, index: int) -> int:
    """The index after the ``"`` that closes a double-quoted word whose content starts at ``index``."""
    while index < len(command):
        if command[index] == "\\":
            index += 2
            continue
        if command[index] == '"':
            return index + 1
        index += 1
    raise Unreadable


def _backtick(command: str, index: int) -> tuple[int, bool]:
    """At an unescaped backtick: (the index after its closing backtick, whether the substitution is empty)."""
    end = index + 1
    while end < len(command):
        if command[end] == "`" and not _escaped(command, end):
            return end + 1, end == index + 1
        end += 1
    raise Unreadable


def _dollar(command: str, index: int, word: Word) -> int:
    """At a ``$``: read what follows it into ``word`` and return the next index. ``$(...)``, ``$((...))``, ``${...}``,
    ``$NAME`` and the special parameters expand; ``$'...'`` is literal; a ``$`` before anything else is a literal ``$``."""
    following = command[index + 1:index + 2]
    if following == "(":
        end = _matching_paren(command, index + 1)
        word.expands = True
    elif following == "{":
        end = command.find("}", index + 2)
        if end < 0:
            raise Unreadable
        end += 1
        word.expands = True
    elif following == "'":
        end = index + 2
        while end < len(command) and not (command[end] == "'" and not _escaped(command, end)):
            end += 1
        if end >= len(command):
            raise Unreadable
        end += 1
        word.quoted = True
    elif following and NAME_START.match(following):
        end = NAME_CHARS.match(command, index + 1).end()
        word.expands = True
    elif following and (following.isdigit() or following in "@*#?$!-"):
        end = index + 2
        word.expands = True
    else:
        end = index + 1  # a literal $
    word.text += command[index:end]
    word.raw += command[index:end]
    return end


def lex(command: str) -> tuple[list[dict], bool, list[str]]:
    """The simple commands of ``command``, in order, each ``{"words": [Word], "redirects": [(operator, Word | None)]}``;
    whether an empty backtick substitution sits inside double quotes; and the bodies of unquoted here-documents.
    Raises Unreadable for a command it cannot read to its end."""
    tokens: list[tuple[str, object]] = []
    word: Word | None = None
    line_heredocs: list[tuple[bool, Word]] = []
    bodies: list[str] = []
    empty_in_quotes = False
    index, length = 0, len(command)

    def end_word() -> None:
        nonlocal word
        if word is None:
            return
        if not word.quoted and not word.expands and word.text in ("{", "}"):
            tokens.append(("sep", word.text))  # a group's braces start and end commands
        else:
            if tokens and tokens[-1][0] == "redir" and tokens[-1][1] in ("<<", "<<-"):
                line_heredocs.append((tokens[-1][1] == "<<-", word))
            tokens.append(("word", word))
        word = None

    while index < length:
        char = command[index]
        if char in " \t":
            end_word()
            index += 1
        elif char == "\n":
            end_word()
            tokens.append(("sep", "\n"))
            index += 1
            for strip_tabs, delimiter in line_heredocs:  # here-document bodies follow the line that opened them
                body = []
                while index < length:
                    stop = command.find("\n", index)
                    line = command[index:] if stop < 0 else command[index:stop]
                    index = length if stop < 0 else stop + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delimiter.text:
                        break
                    body.append(line)
                if not delimiter.quoted:
                    bodies.append("\n".join(body))
            line_heredocs = []
        elif char == "#" and word is None:
            stop = command.find("\n", index)
            index = length if stop < 0 else stop  # a comment runs to the end of its line
        elif char == "\\":
            if index + 1 < length and command[index + 1] == "\n":
                index += 2  # a line continuation joins two lines into one word or command
                continue
            word = word or Word()
            word.text += command[index + 1:index + 2]
            word.raw += command[index:index + 2]
            word.quoted = True
            index += 2
        elif char == "'":
            end = command.find("'", index + 1)
            if end < 0:
                raise Unreadable
            word = word or Word()
            word.text += command[index + 1:end]
            word.raw += command[index:end + 1]
            word.quoted = True
            index = end + 1
        elif char == '"':
            word = word or Word()
            word.quoted = True
            word.raw += '"'
            index += 1
            while True:
                if index >= length:
                    raise Unreadable
                inner = command[index]
                if inner == '"':
                    word.raw += '"'
                    index += 1
                    break
                if inner == "\\":
                    following = command[index + 1:index + 2]
                    word.text += following if following in '$`"\\\n' else "\\" + following
                    word.raw += command[index:index + 2]
                    index += 2
                elif inner == "$":
                    index = _dollar(command, index, word)
                elif inner == "`":
                    end, empty = _backtick(command, index)
                    empty_in_quotes = empty_in_quotes or empty
                    word.text += command[index:end]
                    word.raw += command[index:end]
                    word.expands = True
                    index = end
                else:
                    word.text += inner
                    word.raw += inner
                    index += 1
        elif char == "$":
            word = word or Word()
            index = _dollar(command, index, word)
        elif char == "`":
            end, _ = _backtick(command, index)
            word = word or Word()
            word.text += command[index:end]
            word.raw += command[index:end]
            word.expands = True
            index = end
        elif char in "<>" and command[index + 1:index + 2] == "(":
            end = _matching_paren(command, index + 1)  # a process substitution is a word
            word = word or Word()
            word.text += command[index:end]
            word.raw += command[index:end]
            word.expands = True
            index = end
        elif char in "<>":
            if word is not None and word.text.isdigit() and not word.quoted and not word.expands:
                word = None  # the file descriptor of this redirect
            end_word()
            operator = next(op for op in REDIRECTS if command.startswith(op, index))
            tokens.append(("redir", operator))
            index += len(operator)
        elif char == "&" and command.startswith((">", ">>"), index + 1):
            end_word()
            operator = "&>>" if command.startswith("&>>", index) else "&>"
            tokens.append(("redir", operator))
            index += len(operator)
        elif char in ";&|()":
            end_word()
            separator = next(op for op in SEPARATORS if command.startswith(op, index))
            tokens.append(("sep", separator))
            index += len(separator)
        else:
            word = word or Word()
            word.text += char
            word.raw += char
            index += 1
    end_word()

    commands: list[dict] = []
    current: dict = {"words": [], "redirects": []}
    for kind, value in tokens:
        if kind == "sep":
            if current["words"] or current["redirects"]:
                commands.append(current)
            current = {"words": [], "redirects": []}
        elif kind == "redir":
            current["redirects"].append([value, None])
        elif current["redirects"] and current["redirects"][-1][1] is None:
            current["redirects"][-1][1] = value  # the operand of the redirect before it
        else:
            current["words"].append(value)
    if current["words"] or current["redirects"]:
        commands.append(current)
    return commands, empty_in_quotes, bodies


def _peel(words: list[Word]) -> list[Word]:
    """The command's own words: past its assignments, the reserved words that open it, and the wrappers Grok looks
    through (env with its options and NAME=value words, timeout with its options and duration, and the rest with
    their options)."""
    while words:
        first = words[0]
        if ASSIGNMENT.match(first.raw):  # the name and = are unquoted; the value may be quoted
            words = words[1:]
        elif not first.quoted and first.text in KEYWORDS:
            words = words[1:]
        elif first.text.rsplit("/", 1)[-1] in WRAPPERS and not first.expands:
            program, words = first.text.rsplit("/", 1)[-1], words[1:]
            while words and (words[0].text.startswith("-") or (program == "env" and ASSIGNMENT.match(words[0].raw))):
                if program == "env" and words[0].text in ("-u", "--unset", "-C", "--chdir") and len(words) > 1:
                    words = words[1:]
                elif program in ("timeout", "nice", "ionice", "stdbuf") and words[0].text in (
                        "-s", "--signal", "-k", "--kill-after", "-n", "--adjustment", "-c", "--class", "-p", "-i", "-o",
                        "-e") and len(words) > 1:
                    words = words[1:]
                words = words[1:]
            if program in ("timeout", "chrt") and words:
                words = words[1:]  # the duration, or the priority
        else:
            break
    return words


def write_targets(program: str, arguments: list[Word]) -> list[Word]:
    """What ``program`` writes, from its argument words: every operand of mkdir, touch, rm and tee; the destination of
    cp, mv and ln (the value of a separate -t, else the last of two or more operands)."""
    values = OPTION_VALUES.get(program, ())
    operands, target_directory, index, options = [], None, 0, True
    while index < len(arguments):
        argument = arguments[index]
        text = argument.text
        if options and text == "--":
            options = False
        elif options and program in DESTINATION and text in TARGET_DIRECTORY and index + 1 < len(arguments):
            target_directory = arguments[index + 1]
            index += 1
        elif options and text in values and index + 1 < len(arguments):
            index += 1
        elif options and text.startswith("-") and text != "-":
            pass
        else:
            operands.append(argument)
        index += 1
    if program in EVERY_OPERAND:
        return operands
    if target_directory is not None:
        return [target_directory]
    return operands[-1:] if len(operands) > 1 else []


def floor_shapes(command: str, cwd: str | None = None) -> list[str]:
    """The shapes of ``command`` that Grok 1.0.77's headless Auto-review refuses before its classifier, sorted; an empty
    list for every other command, and for one the lexer cannot read. ``cwd`` is the session's own folder."""
    try:
        commands, empty_in_quotes, bodies = lex(command)
    except (Unreadable, IndexError, StopIteration, ValueError):
        return []
    shapes, moved = set(), False
    for position, simple in enumerate(commands):
        words = _peel(simple["words"])
        program = words[0].text.rsplit("/", 1)[-1] if words and not words[0].expands else None
        if program in ("cd", "pushd"):
            target = words[1].text if len(words) > 1 else "~"
            at_home = position == 0 and cwd is not None and target.rstrip("/") == cwd.rstrip("/")
            moved = moved or not at_home
            continue
        targets = write_targets(program, words[1:]) if program in EVERY_OPERAND | DESTINATION else []
        if any(target.expands for target in targets):
            shapes.add("var-write")
        elif moved and any(not target.text.startswith("/") for target in targets):
            shapes.add("cd-relative-write")
        for operator, target in simple["redirects"]:
            if (moved and operator in WRITE_REDIRECTS and target is not None and not target.expands
                    and not target.text.startswith("/")):
                shapes.add("cd-relative-write")
    if empty_in_quotes or any(_has_empty_backtick(body) for body in bodies):
        shapes.add("backtick-in-dq")
    return sorted(shapes)


def _has_empty_backtick(text: str) -> bool:
    """An empty backtick substitution in text that expands like a double-quoted word (an unquoted here-document)."""
    index = 0
    while index < len(text):
        if text[index] == "`" and not _escaped(text, index):
            try:
                end, empty = _backtick(text, index)
            except Unreadable:
                return False
            if empty:
                return True
            index = end
        else:
            index += 1
    return False


def reason(shapes: list[str]) -> str:
    """The deny reason the model reads: why the command was not run and how to write it so that Grok can check it."""
    why = "; ".join(SHAPE_WORDS[shape] for shape in shapes)
    return (f"{MARK} before it ran, and that refusal would end the session, because it cannot tell which files the "
            f"command writes ({why}). {REWRITE}")


def decide(payload: dict) -> dict | None:
    """The hook's reply to one PreToolUse event: a deny for a floored shell command under Auto-review, else None."""
    if payload.get("toolName") != SHELL_TOOL or payload.get("toolInputTruncated"):
        return None  # a cut command hides its end, so its shapes are unknown: Grok decides
    if payload.get("permissionMode") != ACTIVE_MODE:
        return None  # another mode (bypassPermissions, default, plan) has no floor to foresee
    command = (payload.get("toolInput") or {}).get("command")
    if not isinstance(command, str):
        return None
    shapes = floor_shapes(command, payload.get("cwd") or payload.get("workspaceRoot"))
    return {"decision": "deny", "reason": reason(shapes), "shapes": shapes} if shapes else None


def log_path(environ: dict | None = None) -> Path | None:
    """Where the hook records its denials: the run's own state folder, which the harness's throwaway profile names in
    XDG_STATE_HOME (an absolute path). None, and no record, anywhere else."""
    environ = os.environ if environ is None else environ
    state = environ.get("XDG_STATE_HOME")
    if not state or not os.path.isabs(state):
        return None
    return Path(state) / "shiploop-e2e" / f"{NAME}.jsonl"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        decision = decide(payload) if isinstance(payload, dict) else None
        if decision is None:
            return 0
        command = (payload.get("toolInput") or {}).get("command") or ""
        path = log_path()
        if path is not None:
            try:
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


def _calibration(script: Path) -> str | None:
    """The build the installed copy's rule was calibrated on, read from that copy (not from this module)."""
    match = re.search(r'^CALIBRATED_BUILD = "([^"]+)"', script.read_text(errors="replace"), re.M)
    return match.group(1) if match else None


def installed(grok_dir: Path) -> dict | None:
    """The record of the hook a profile already holds (``kept``: it was there before this launch), or None for a profile
    without it. Reads only: a regrade, which starts no host, reports what the run had and writes nothing into it."""
    hooks = Path(grok_dir) / "hooks"
    script, config = hooks / f"{NAME}.py", hooks / f"{NAME}.json"
    if not (script.is_file() and config.is_file()):
        return None
    return {"installed": True, "kept": True, "script": str(script),
            "sha256": hashlib.sha256(script.read_bytes()).hexdigest(), "calibrated_on": _calibration(script)}


def install(grok_dir: Path) -> dict:
    """Copy this module into ``grok_dir``/hooks and register it as a PreToolUse hook on Grok's shell tool, before the
    session starts (headless Grok reads its global hooks only then). A profile that already has the hook keeps it, so a
    resumed run keeps the hook it started with; ``kept`` False on a resumed run says the hook arrived at that resume.
    The command runs under ``sh -c`` (a hook without ``args``), and ``|| true`` keeps an interpreter that cannot start
    the script (exit 2, which Grok reads as a deny) from refusing every shell call. Returns the record result.json keeps."""
    record = installed(grok_dir)
    if record is not None:
        return record
    hooks = Path(grok_dir) / "hooks"
    script, config = hooks / f"{NAME}.py", hooks / f"{NAME}.json"
    hooks.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve(), script)
    config.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": SHELL_TOOL, "hooks": [
        {"type": "command", "command": shlex.join(["python3", str(script)]) + " || true",
         "timeout": HOOK_TIMEOUT_SECONDS}]}]}}, indent=2) + "\n")
    return {**installed(grok_dir), "kept": False}


def denials(home: Path) -> dict:
    """What the hook logged as denied in a run's throwaway profile at ``home``: the count, by shape, and each command's
    head. A row it cannot read is counted in ``unreadable`` and a log it cannot open leaves ``error``; never raises."""
    path = log_path({"XDG_STATE_HOME": str(Path(home).resolve() / ".local" / "state")})
    found = {"count": 0, "shapes": {}, "commands": [], "unreadable": 0}
    try:
        lines = path.read_text(errors="replace").splitlines() if path and path.is_file() else []
    except OSError as error:
        return {**found, "error": type(error).__name__}
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        shapes = row.get("shapes") if isinstance(row, dict) else None
        if not isinstance(shapes, list) or not all(isinstance(shape, str) for shape in shapes):
            found["unreadable"] += 1
            continue
        found["count"] += 1
        for shape in shapes:
            found["shapes"][shape] = found["shapes"].get(shape, 0) + 1
        found["commands"].append(str(row.get("command", ""))[:160])
    return found


if __name__ == "__main__":
    raise SystemExit(main())
