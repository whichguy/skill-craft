"""Narrow, non-interactive Grok helpers for the opt-in ShipLoop E2E harness.

The adapter deliberately records only observable transport facts.  In particular,
an advertised slash command or a completed shell tool call is not evidence that
the model followed ShipLoop correctly or that a product was delivered.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
from typing import Any, Iterable, Mapping


INSPECT_TIMEOUT_SECONDS = 30
SHIPLOOP_SKILL_NAME = "shiploop"
IMPROVE_SKILL_NAME = "improve"
_SELECTED_SKILL_NAMES = frozenset((SHIPLOOP_SKILL_NAME, IMPROVE_SKILL_NAME))
NATIVE_STREAM_FORMAT = "streaming-json"
DEFAULT_REASONING_EFFORT = "xhigh"
# The current ShipLoop CLI verbs, exactly as ``shiploop --help`` lists them.
SHIPLOOP_DIRECT_SUBCOMMANDS = frozenset(
    {
        "workspace",
        "chain",
        "graph-dry-run",
        "init",
        "delegation",
        "lint-mode",
        "lint",
        "improve-bind",
        "improve-complete",
        "improve-reconcile",
        "next",
        "report",
        "context",
        "complete",
        "halt",
        "pause",
        "resume",
    }
)
_SHELL_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
_SHELL_VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_SHELL_SEPARATORS = frozenset({";", "|", "||", "&", "&&"})
_UNATTRIBUTABLE_SHELL_OPERATORS = frozenset({"|", "||", "&", "&&"})
_UNATTRIBUTABLE_SHELL_WORDS = frozenset(
    {
        "!",
        "(",
        ")",
        "{",
        "}",
        "[[",
        "]]",
        "((",
        "))",
        "if",
        "then",
        "elif",
        "else",
        "fi",
        "for",
        "while",
        "until",
        "select",
        "do",
        "done",
        "case",
        "esac",
        "function",
        "coproc",
        "exit",
        "return",
        "exec",
        "eval",
        ".",
        "source",
        "set",
        "trap",
        "alias",
        "unalias",
        "builtin",
        "command",
    }
)
_PYTHON_HEREDOC_HEADER = re.compile(r"^[ \t]*python3[ \t]+-[ \t]+<<'PY'[ \t]*$")


class GrokAdapterError(RuntimeError):
    """Raised when a local Grok preflight or capture cannot be interpreted."""


def _absolute(path: str | Path) -> Path:
    return Path(path).expanduser().absolute()


def _skill_file(path: Path) -> Path:
    candidate = path / "SKILL.md" if path.is_dir() else path
    if candidate.name != "SKILL.md" or not candidate.is_file():
        raise GrokAdapterError("expected ShipLoop skill must be an existing SKILL.md file or its directory")
    return candidate.resolve()


def _skill_records(value: Any, skill_name: str) -> Iterable[dict[str, Any]]:
    """Yield user-invocable records for one fixed selected skill.

    ``grok inspect`` also reports agent cards.  An agent card may share the
    ShipLoop name but is not a slash-invocable skill, so it must not make an
    otherwise selected skill ambiguous.
    """
    if isinstance(value, dict):
        if (
            value.get("name") == skill_name
            and value.get("userInvocable") is True
        ):
            yield value
        for child in value.values():
            yield from _skill_records(child, skill_name)
    elif isinstance(value, list):
        for child in value:
            yield from _skill_records(child, skill_name)


def _require_literal_shiploop_route(record: Mapping[str, Any]) -> None:
    """Fail closed when inspect cannot prove that ``/shiploop`` is this card."""
    invocable_as = record.get("invocableAs")
    collides_with = record.get("collidesWith")
    collision = bool(collides_with)
    if invocable_as in (None, SHIPLOOP_SKILL_NAME) and not collision:
        return
    details: list[str] = []
    if collision:
        details.append("a ShipLoop collision")
    if invocable_as is not None and invocable_as != SHIPLOOP_SKILL_NAME:
        details.append("a nonliteral invocableAs")
    observed = ", ".join(details) or "an unverifiable literal route"
    raise GrokAdapterError(
        "grok inspect reports " + observed
        + "; literal /shiploop cannot be proven to select the expected source. "
        + "Resolve the source selection in Grok, then rerun the audit from the product directory."
    )


def inspect_selection(
    grok_bin: str,
    repo: Path,
    expected_skill: Path | None = None,
    env: Mapping[str, str] | None = None,
    *,
    skill_name: str = SHIPLOOP_SKILL_NAME,
) -> dict[str, Any]:
    """Verify that Grok discovers exactly one selected user-invocable skill.

    ``grok inspect`` does not have a ``--cwd`` flag, so the subprocess is started
    in ``repo``.  The returned dictionary intentionally excludes the full inspect
    document, which can describe unrelated local configuration.
    """
    if skill_name not in _SELECTED_SKILL_NAMES:
        raise GrokAdapterError("selected skill must be ShipLoop or Improve")
    repo_path = _absolute(repo)
    if not repo_path.is_dir():
        raise GrokAdapterError("inspection repository must be an existing directory")
    if skill_name == SHIPLOOP_SKILL_NAME and expected_skill is None:
        raise GrokAdapterError("expected ShipLoop skill is required")
    if skill_name == IMPROVE_SKILL_NAME and expected_skill is not None:
        raise GrokAdapterError("Improve selection must come from grok inspect")
    expected_path = _skill_file(_absolute(expected_skill)) if expected_skill is not None else None
    if not isinstance(grok_bin, str) or not grok_bin.strip():
        raise GrokAdapterError("grok binary path is required")

    try:
        result = subprocess.run(
            [grok_bin, "inspect", "--json"],
            cwd=repo_path,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=INSPECT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GrokAdapterError("grok inspect timed out") from exc
    except OSError as exc:
        raise GrokAdapterError(f"could not start grok inspect: {exc.__class__.__name__}") from exc

    if result.returncode != 0:
        raise GrokAdapterError(f"grok inspect exited with status {result.returncode}")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GrokAdapterError("grok inspect did not return JSON") from exc

    matching_records: list[tuple[dict[str, Any], Path, Path]] = []
    discovered_realpaths: set[Path] = set()
    malformed = False
    for record in _skill_records(document, skill_name):
        source = record.get("source")
        if not isinstance(source, Mapping):
            malformed = True
            continue
        source_path_value = source.get("path")
        if not isinstance(source_path_value, str) or not source_path_value:
            malformed = True
            continue
        selected_path = _absolute(source_path_value)
        if not selected_path.is_file():
            malformed = True
            continue
        selected_realpath = selected_path.resolve()
        discovered_realpaths.add(selected_realpath)
        if expected_path is None or selected_realpath == expected_path:
            matching_records.append((record, selected_path, selected_realpath))

    label = "ShipLoop" if skill_name == SHIPLOOP_SKILL_NAME else "Improve"
    if skill_name == IMPROVE_SKILL_NAME and malformed:
        raise GrokAdapterError("grok inspect reports a malformed user-invocable Improve skill")
    if len(matching_records) != 1:
        raise GrokAdapterError(
            f"grok inspect must report exactly one matching user-invocable {label} skill"
        )
    if len(discovered_realpaths) != 1:
        if skill_name == IMPROVE_SKILL_NAME:
            raise GrokAdapterError(
                "grok inspect reports multiple distinct existing user-invocable Improve sources; "
                "resolve the source selection in Grok, then rerun the audit from the product directory."
            )
        raise GrokAdapterError(
            "grok inspect reports multiple distinct existing user-invocable ShipLoop sources; "
            "literal /shiploop cannot be proven to select the expected source. "
            "Resolve the source selection in Grok, then rerun the audit from the product directory."
        )

    record, selected_path, selected_realpath = matching_records[0]
    source = record["source"]
    if skill_name == SHIPLOOP_SKILL_NAME:
        _require_literal_shiploop_route(record)

    return {
        "skill": skill_name,
        "source": {
            "path": str(selected_path),
            "realpath": str(selected_realpath),
            "type": source.get("type") if isinstance(source.get("type"), str) else None,
            "user_invocable": True,
            "invocable_as": record.get("invocableAs"),
            "collides_with": record.get("collidesWith"),
        },
        "expected": {
            "path": str(expected_path) if expected_path is not None else None,
            "realpath": str(expected_path) if expected_path is not None else None,
        },
    }


def _required_nonempty(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GrokAdapterError(f"{label} is required")
    return value.strip()


def resolve_reasoning_effort(value: str | None) -> str:
    """Pin omitted effort rather than inheriting an unknown host default."""
    return DEFAULT_REASONING_EFFORT if value is None else _required_nonempty(value, "reasoning effort")


def build_argv(
    grok_bin: str,
    prompt_file: Path,
    repo: Path,
    model: str,
    max_turns: int,
    permission_mode: str = "default",
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    background_wait_timeout_seconds: float = 7200,
) -> list[str]:
    """Build a literal, fresh-session Grok headless invocation.

    A prompt file triggers Grok's one-shot headless mode without placing prompt
    text in argv.  This function intentionally does not add an always-approve
    mode: callers must opt in through ``permission_mode``.
    """
    binary = _required_nonempty(grok_bin, "grok binary path")
    repo_path = _absolute(repo)
    prompt_path = _absolute(prompt_file)
    if not repo_path.is_dir():
        raise GrokAdapterError("repository must be an existing directory")
    if not prompt_path.is_file():
        raise GrokAdapterError("prompt file must be an existing file")
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns < 1:
        raise GrokAdapterError("max_turns must be a positive integer")
    if (isinstance(background_wait_timeout_seconds, bool)
            or not isinstance(background_wait_timeout_seconds, (int, float))
            or not math.isfinite(background_wait_timeout_seconds)
            or background_wait_timeout_seconds <= 0):
        raise GrokAdapterError("background wait timeout must be a positive finite number")
    # Grok's hidden headless flag accepts whole seconds. Round upward so its
    # internal wait cannot expire before the observer's wall-clock cap.
    background_wait_timeout = math.ceil(background_wait_timeout_seconds)

    argv = [
        binary,
        "--cwd",
        str(repo_path),
        "--prompt-file",
        str(prompt_path),
        "--verbatim",
        "--output-format",
        NATIVE_STREAM_FORMAT,
        "--model",
        _required_nonempty(model, "model"),
        "--max-turns",
        str(max_turns),
        "--background-wait-timeout",
        str(background_wait_timeout),
        "--permission-mode",
        _required_nonempty(permission_mode, "permission mode"),
        "--no-auto-update",
    ]
    argv.extend(["--reasoning-effort", resolve_reasoning_effort(reasoning_effort)])
    return argv


def _shiploop_command_route(command: Any) -> str | None:
    if isinstance(command, str):
        token = command.strip().split(maxsplit=1)[0] if command.strip() else ""
        if token in ("/shiploop", SHIPLOOP_SKILL_NAME):
            return token
        if token.startswith("/") and token.endswith(f":{SHIPLOOP_SKILL_NAME}"):
            return token
        return None
    if isinstance(command, dict):
        for key in ("name", "command"):
            route = _shiploop_command_route(command.get(key))
            if route is not None:
                return route
    return None


def _accepted_cli_paths(selected_cli: Path) -> tuple[set[str], set[str]]:
    """Accept an explicit CLI path through either its symlink or real package root."""
    cli_path = _absolute(selected_cli)
    real_cli = cli_path.resolve()
    candidates = {
        cli_path,
        real_cli,
        cli_path.parent.parent / "scripts" / "shiploop",
        real_cli.parent.parent / "scripts" / "shiploop",
    }
    textual = {str(path) for path in candidates}
    resolved = {str(path.resolve()) for path in candidates}
    return textual, resolved


def _path_matches_selected_cli(token: str, textual_paths: set[str], resolved_paths: set[str]) -> bool:
    candidate = Path(token).expanduser()
    if not candidate.is_absolute():
        return False
    if str(candidate) in textual_paths:
        return True
    return str(candidate.resolve()) in resolved_paths


def _command_values(raw_input: dict[str, Any]) -> Iterable[Any]:
    for key in ("command", "cmd", "command_line", "commandLine", "argv", "args", "script"):
        if key in raw_input:
            yield raw_input[key]


def _shell_line_context(line: str, quote: str | None) -> tuple[str | None, bool]:
    """Return quote state and whether the physical line continues a command."""
    content = line.rstrip("\r\n")
    index = 0
    while index < len(content):
        char = content[index]
        if quote == "'":
            if char == "'":
                quote = None
            index += 1
            continue
        if char == "\\":
            if index + 1 == len(content):
                return quote, True
            index += 2
            continue
        if quote == '"':
            if char == '"':
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char == "#":
            break
        index += 1
    return quote, False


def _standalone_python_completion_callback(line: str) -> bool:
    """Recognize the one terminal completion callback allowed after a heredoc."""
    if "$(" in line or "`" in line or "$" in line or "#" in line:
        return False
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";|&")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        tokens = list(lexer)
    except ValueError:
        return False
    if any(token in _SHELL_SEPARATORS for token in tokens):
        return False
    return (
        len(tokens) >= 3
        and tokens[0] == "python3"
        and tokens[2] in {"complete", "improve-complete"}
    )


def _strip_supported_python_heredoc(value: str) -> str | None:
    """Remove one exact Python heredoc body while retaining its callback line.

    The body is opaque: no token, path, or command-looking text in it can count
    as an invocation.  This intentionally supports only a standalone
    ``python3 - <<'PY'`` header, an exact ``PY`` terminator, and one standalone
    literal ``python3 <selected-cli> complete ...`` or
    ``python3 <selected-cli> improve-complete ...`` line after the terminator.
    All other heredoc forms remain unsupported and are rejected downstream.
    """
    lines = value.splitlines(keepends=True)
    quote: str | None = None
    continued = False
    header_index: int | None = None
    for index, line in enumerate(lines):
        if (
            quote is None
            and not continued
            and _PYTHON_HEREDOC_HEADER.fullmatch(line.rstrip("\r\n"))
        ):
            header_index = index
            break
        quote, continued = _shell_line_context(line, quote)

    if header_index is None:
        return value

    delimiter_index: int | None = None
    for index in range(header_index + 1, len(lines)):
        if lines[index] in {"PY\n", "PY\r\n", "PY\r", "PY"}:
            delimiter_index = index
            break
    if delimiter_index is None:
        return None

    suffix_lines = lines[delimiter_index + 1 :]
    nonblank_suffix = [line.rstrip("\r\n") for line in suffix_lines if line.strip(" \t\r\n")]
    if len(nonblank_suffix) != 1 or not _standalone_python_completion_callback(nonblank_suffix[0]):
        return None

    prefix = "".join(lines[:header_index])
    return prefix + "\n" + nonblank_suffix[0]


def _normalize_shell_newlines(value: str) -> str | None:
    """Add command separators at safe physical-line boundaries.

    This is a deliberately small lexer, not shell execution.  It preserves
    quoted multiline values, removes only shell line-continuation backslashes,
    and places a separator *after* a newline so ``shlex`` can discard a comment
    before it sees the next command. A single exact Python heredoc may be
    stripped by ``_strip_supported_python_heredoc``; other forms are rejected.
    """
    value = _strip_supported_python_heredoc(value)
    if value is None:
        return None
    output: list[str] = []
    quote: str | None = None
    in_comment = False
    index = 0
    while index < len(value):
        char = value[index]
        next_char = value[index + 1] if index + 1 < len(value) else ""

        if in_comment:
            if char == "\n":
                output.append("\n;")
                in_comment = False
            else:
                output.append(char)
            index += 1
            continue

        if quote == "'":
            output.append(char)
            if char == "'":
                quote = None
            index += 1
            continue

        if char == "\\":
            if next_char == "\n":
                index += 2
                continue
            if next_char == "\r" and index + 2 < len(value) and value[index + 2] == "\n":
                index += 3
                continue
            output.append(char)
            if next_char:
                output.append(next_char)
                index += 2
            else:
                index += 1
            continue

        if quote == '"':
            output.append(char)
            if char == '"':
                quote = None
            index += 1
            continue

        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue
        if char == "#":
            in_comment = True
            output.append(char)
            index += 1
            continue
        if char == "<" and next_char == "<":
            return None
        if char == "\n":
            output.append("\n;")
        else:
            output.append(char)
        index += 1
    return "".join(output)


def _token_segments(value: Any) -> list[list[str]]:
    """Tokenize a shell command without evaluating it.

    The capture must not execute or consult shell state while interpreting a
    tool event. Semicolon, shell-operator, and safe unquoted newline boundaries
    are retained only to identify individual command positions. Conditional,
    pipeline, and background operators make branch execution unprovable from a
    single host-tool event, so string commands containing them are rejected.
    Semicolon-only sequences remain structurally observable.
    """
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [list(value)]
    if not isinstance(value, str):
        return []
    normalized = _normalize_shell_newlines(value)
    if normalized is None:
        return []
    try:
        lexer = shlex.shlex(normalized, posix=True, punctuation_chars=";|&")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        tokens = list(lexer)
    except ValueError:
        return []
    if any(token in _UNATTRIBUTABLE_SHELL_OPERATORS for token in tokens):
        return []

    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _expand_static_word(value: str, variables: Mapping[str, str]) -> str | None:
    """Expand only literal variables assigned earlier in the same input.

    This deliberately refuses command substitution, backticks, unknown names,
    and other dollar expressions.  It is not a shell evaluator.
    """
    if "$(" in value or "`" in value:
        return None
    unresolved = False

    def replace(match: re.Match[str]) -> str:
        nonlocal unresolved
        name = match.group(1) or match.group(2)
        replacement = variables.get(name)
        if replacement is None:
            unresolved = True
            return ""
        return replacement

    expanded = _SHELL_VARIABLE.sub(replace, value)
    if unresolved or "$" in expanded:
        return None
    return expanded


def _expanded_command(segment: list[str], variables: dict[str, str]) -> list[str] | None:
    """Return one command after safe leading assignment expansion."""
    command: list[str] = []
    for token in segment:
        if not command:
            assignment = _SHELL_ASSIGNMENT.match(token)
            if assignment is not None:
                value = _expand_static_word(assignment.group(2), variables)
                if value is None:
                    return None
                variables[assignment.group(1)] = value
                continue
        expanded = _expand_static_word(token, variables)
        if expanded is None:
            return None
        command.append(expanded)
    return command


def _is_python_executable(token: str) -> bool:
    name = Path(token).name
    return name in {"python", "python3"}


def _command_argv_tail(
    command: list[str], textual_paths: set[str], resolved_paths: set[str]
) -> list[str] | None:
    """Return the ShipLoop argv tail for a real execution position."""
    if len(command) >= 2 and _is_python_executable(command[0]):
        if _path_matches_selected_cli(command[1], textual_paths, resolved_paths):
            return command[2:]
    if (
        len(command) >= 2
        and _path_matches_selected_cli(command[0], textual_paths, resolved_paths)
        and command[1] in SHIPLOOP_DIRECT_SUBCOMMANDS
    ):
        return command[1:]
    return None


def _unattributable_shell_segment(command: list[str]) -> bool:
    """Identify shell control that can make a later command conditionally unreachable.

    This is intentionally a deny-list, not shell interpretation.  Ordinary
    setup commands (for example ``git`` and ``node``) may precede a terminal
    callback.  Commands that can terminate, replace, define, or control the
    shell make execution of that callback unknowable from the host tool's final
    status, so the complete input is left unattributed.
    """
    if not command:
        return False
    first = command[0]
    return (
        first in _UNATTRIBUTABLE_SHELL_WORDS
        or first.endswith("()")
        or (len(command) >= 2 and command[1] == "()")
    )


def _cli_invocations(event: dict[str, Any], textual_paths: set[str], resolved_paths: set[str]) -> list[list[str]]:
    """Return a structurally attributable terminal ShipLoop execution.

    A source path in ``cat``, ``echo``, ``grep``, or free-form text is not an
    invocation.  Static same-command assignment expansion is intentionally
    narrow and never evaluates shell syntax.  For string commands, a selected
    CLI must be the final nonempty shell segment: host-tool completion and exit
    status otherwise describe a trailing command instead.  Any unparseable
    prefix or terminal/control shell segment leaves the whole input unknown.
    """
    raw_input = event.get("rawInput")
    if not isinstance(raw_input, dict):
        return []
    invocations: list[list[str]] = []
    for value in _command_values(raw_input):
        variables: dict[str, str] = {}
        segments = _token_segments(value)
        if not segments:
            continue
        commands: list[list[str]] = []
        for segment in segments:
            command = _expanded_command(segment, variables)
            if command is None:
                commands = []
                break
            if _unattributable_shell_segment(command):
                commands = []
                break
            commands.append(command)
        if not commands or len(commands) != len(segments):
            continue
        argv_tail = _command_argv_tail(commands[-1], textual_paths, resolved_paths)
        if argv_tail is not None:
            invocations.append(argv_tail)
    return invocations


def _reported_exit_code(event: dict[str, Any]) -> int | None:
    """Read terminal exit evidence; interim Grok updates may contain zero placeholders."""
    status = event.get("status")
    if not isinstance(status, str) or status.lower() not in {"completed", "failed"}:
        return None
    raw_output = event.get("rawOutput")
    if not isinstance(raw_output, dict):
        return None
    for key in ("exitCode", "exit_code"):
        value = raw_output.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _call_id(event: dict[str, Any], line_number: int) -> str:
    for key in ("toolCallId", "tool_call_id"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return f"line:{line_number}"


def _captured_native_event(record: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """Unwrap a capture receipt, accepting only native stdout payloads.

    ``capture.py`` stores a receipt around each emitted line.  Stderr can
    contain JSON-shaped diagnostics, which must never be treated as Grok
    protocol observations.  Bare native events remain supported for direct
    fixtures and externally produced captures.
    """
    is_receipt = (
        isinstance(record.get("stream"), str)
        and "line" in record
        and ("received_at" in record or "timestamp" in record)
    )
    if not is_receipt:
        return record, False
    if record["stream"] != "stdout":
        return None, True
    payload = record.get("payload")
    return (payload, True) if isinstance(payload, dict) else (None, True)


_CONTROL_COMMAND_KEYS = frozenset({"command", "cmd", "commandline", "argv", "args", "script"})
_CONTROL_PATH_KEY_SUFFIXES = ("path", "file", "directory", "folder", "root", "dir")
_CONTROL_PATH_KEYS = frozenset(
    {
        "dir",
        "cwd",
        "repo",
        "repository",
        "workspace",
        "target",
        "source",
        "destination",
        "dest",
        "input",
        "output",
        "location",
    }
)
_CONTROL_PATH_DELIMITERS = frozenset(" \t\r\n'\"`;|&()<>\\")
_NATIVE_READ_TOOLS = frozenset({"read_file", "readfile", "filesystem.read_file"})
_ABSOLUTE_PATH_TOKEN = re.compile(r"(?<![A-Za-z0-9_.~/%+:-])(/[^ \t\r\n'\"`;|&()<>\\]+)")


def _field_name(value: object) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _field_locator(parent: str, key: object) -> str:
    if isinstance(key, str) and key.isidentifier():
        return f"{parent}.{key}"
    return f"{parent}[{key!r}]"


def _control_roots(forbidden_roots: Mapping[str, str | Path]) -> list[dict[str, object]]:
    """Normalize declared observer controls without consulting model output."""
    records: list[dict[str, object]] = []
    for raw_name, raw_path in forbidden_roots.items():
        if not isinstance(raw_name, str) or not raw_name:
            raise GrokAdapterError("control root names must be nonempty strings")
        if not isinstance(raw_path, (str, Path)):
            raise GrokAdapterError("control roots must be paths")
        textual = Path(raw_path).expanduser().absolute()
        if not textual.is_absolute():
            raise GrokAdapterError("control roots must be absolute paths")
        resolved = textual.resolve()
        aliases = []
        for candidate in (textual, resolved):
            normalized = Path(os.path.normpath(str(candidate)))
            if str(normalized) not in aliases:
                aliases.append(str(normalized))
        records.append({"name": raw_name, "path": str(resolved), "aliases": aliases})
    return records


def _normalized_absolute_path(value: str) -> Path | None:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        return None
    return Path(os.path.normpath(str(candidate)))


def _matched_control_roots(path: Path, controls: list[dict[str, object]]) -> list[str]:
    matches: list[str] = []
    candidates = [path]
    try:
        resolved = Path(os.path.normpath(str(path.resolve(strict=False))))
    except OSError:
        resolved = path
    if resolved != path:
        candidates.append(resolved)
    for control in controls:
        aliases = control["aliases"]
        assert isinstance(aliases, list)
        for alias in aliases:
            root = Path(alias)
            if any(candidate == root or candidate.is_relative_to(root) for candidate in candidates):
                matches.append(str(control["name"]))
                break
    return sorted(matches)


def _absolute_path_candidates(value: str, controls: list[dict[str, object]]) -> list[Path]:
    """Extract literal absolute path tokens without evaluating shell syntax."""
    candidates: list[Path] = []
    direct = _normalized_absolute_path(value)
    if direct is not None:
        candidates.append(direct)
    candidates.extend(
        candidate
        for match in _ABSOLUTE_PATH_TOKEN.finditer(value)
        if (candidate := _normalized_absolute_path(match.group(1))) is not None
    )
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=";|&")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        candidates.extend(
            candidate
            for token in lexer
            if (candidate := _normalized_absolute_path(token)) is not None
        )
    except ValueError:
        # An unbalanced quote remains unproven rather than being evaluated.
        pass
    # A declared root can contain spaces, which a generic shell-token scanner
    # cannot retain. Keep that path literal support without scanning model text.
    for control in controls:
        aliases = control["aliases"]
        assert isinstance(aliases, list)
        for raw_root in aliases:
            root = str(raw_root).rstrip("/") or "/"
            start = 0
            while True:
                index = value.find(root, start)
                if index < 0:
                    break
                before = value[index - 1] if index else ""
                end = index + len(root)
                after = value[end] if end < len(value) else ""
                left_safe = not before or not (before.isalnum() or before in "._~/%+-:")
                right_safe = not after or after == "/" or after in _CONTROL_PATH_DELIMITERS
                if left_safe and right_safe:
                    finish = end
                    while finish < len(value) and value[finish] not in _CONTROL_PATH_DELIMITERS:
                        finish += 1
                    candidate = _normalized_absolute_path(value[index:finish])
                    if candidate is not None:
                        candidates.append(candidate)
                start = end
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if str(candidate) not in seen:
            unique.append(candidate)
            seen.add(str(candidate))
    return unique


def _path_references_in_string(value: str, controls: list[dict[str, object]]) -> list[tuple[str, list[str]]]:
    """Return lexically absolute control paths with token-safe boundaries.

    This deliberately recognizes literal absolute paths only. It does not decode
    shell escapes, URLs, relative paths, or encoded arguments.
    """
    found: list[tuple[str, list[str]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for candidate in _absolute_path_candidates(value, controls):
        matched = _matched_control_roots(candidate, controls)
        if not matched:
            continue
        key = (str(candidate), tuple(matched))
        if key not in seen:
            found.append((str(candidate), matched))
            seen.add(key)
    return found


def _is_path_field(key: object) -> bool:
    normalized = _field_name(key)
    return normalized in _CONTROL_PATH_KEYS or normalized.endswith(_CONTROL_PATH_KEY_SUFFIXES)


def _is_command_field(key: object) -> bool:
    return _field_name(key) in _CONTROL_COMMAND_KEYS


def _input_path_references(
    value: object,
    controls: list[dict[str, object]],
    locator: str = "rawInput",
    path_context: bool = False,
    command_context: bool = False,
) -> Iterable[tuple[str, str, list[str]]]:
    """Walk only path-shaped or command-shaped rawInput string leaves."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _input_path_references(
                child,
                controls,
                _field_locator(locator, key),
                path_context or _is_path_field(key),
                command_context or _is_command_field(key),
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _input_path_references(child, controls, f"{locator}[{index}]", path_context, command_context)
        return
    if not isinstance(value, str) or not (path_context or command_context):
        return
    for path, matched in _path_references_in_string(value, controls):
        yield locator, path, matched


def _tool_name(event: Mapping[str, object]) -> str:
    for key in ("toolName", "tool_name", "tool", "name"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return "<unknown>"


def observe_control_input_references(
    events_file: Path,
    forbidden_roots: Mapping[str, str | Path],
) -> dict[str, object]:
    """Record observed model tool-input references to observer control paths.

    The observer examines only structured ``tool_call.rawInput`` values from
    native stdout events. It records attempted literal input references; it does
    not claim to prove all filesystem accesses or inspect tool output content.
    """
    controls = _control_roots(forbidden_roots)
    result: dict[str, object] = {
        "schema_version": 1,
        "scope": "Structured stdout tool_call rawInput only; top-level observer argv and model text/output are excluded.",
        "controls": [{"name": item["name"], "path": item["path"]} for item in controls],
        "references": [],
        "exposure_observed": False,
        "observation_complete": False,
        "status": "control-input-observation-unavailable",
        "limitations": [
            "A literal input reference can invalidate a trial even when successful file access is not observed.",
            "Relative, encoded, or unreported accesses are outside this observation and are not claimed absent.",
            "No filesystem sandbox or universal read-proof is provided by this observer.",
        ],
    }
    event_path = _absolute(events_file)
    try:
        lines = event_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        result["error"] = f"event capture unavailable: {exc.__class__.__name__}"
        return result

    updates: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    calls: list[tuple[int, dict[str, object]]] = []
    invalid_lines: list[int] = []
    non_object_lines: list[int] = []
    malformed_stdout_event_lines: set[int] = set()
    native_stdout_events = 0
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines.append(line_number)
            continue
        if not isinstance(record, dict):
            non_object_lines.append(line_number)
            continue
        native_event, is_receipt = _captured_native_event(record)
        if native_event is None:
            if is_receipt and record.get("stream") == "stdout":
                malformed_stdout_event_lines.add(line_number)
            continue
        event_type = native_event.get("type")
        if not isinstance(event_type, str) or not event_type:
            malformed_stdout_event_lines.add(line_number)
            continue
        native_stdout_events += 1
        if is_receipt and record.get("stream") == "stdout" and record.get("line_truncated") is True:
            malformed_stdout_event_lines.add(line_number)
        if event_type == "tool_call":
            if isinstance(native_event.get("rawInput"), dict):
                calls.append((line_number, native_event))
            else:
                malformed_stdout_event_lines.add(line_number)
        elif event_type == "tool_call_update":
            updates[_call_id(native_event, line_number)].append(native_event)

    references: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for line_number, event in calls:
        raw_input = event.get("rawInput")
        if not isinstance(raw_input, dict):
            continue
        call_id = _call_id(event, line_number)
        updates_for_call = updates.get(call_id, [])
        statuses = [row["status"] for row in updates_for_call if isinstance(row.get("status"), str)]
        exit_codes = [code for row in updates_for_call if (code := _reported_exit_code(row)) is not None]
        completed = any(status.lower() == "completed" for status in statuses)
        tool = _tool_name(event)
        for field, path, matched_controls in _input_path_references(raw_input, controls):
            key = (call_id, field, path)
            if key in seen:
                continue
            seen.add(key)
            native_read = tool.lower() in _NATIVE_READ_TOOLS
            references.append(
                {
                    "event_line": line_number,
                    "call_id": call_id,
                    "tool": tool,
                    "field": field,
                    "path": path,
                    "matched_control_roots": matched_controls,
                    "attempt": "attempted-input-reference",
                    "completed_status_observed": completed,
                    "zero_exit_code_observed": any(code == 0 for code in exit_codes),
                    "successful_read_observed": bool(native_read and completed and any(code == 0 for code in exit_codes)),
                }
            )
    result["references"] = references
    result["exposure_observed"] = bool(references)
    result["malformed_event_lines"] = invalid_lines
    result["non_object_event_lines"] = non_object_lines
    result["malformed_stdout_event_lines"] = sorted(malformed_stdout_event_lines)
    result["observation_complete"] = bool(native_stdout_events) and not (
        invalid_lines or non_object_lines or malformed_stdout_event_lines
    )
    if references:
        result["status"] = "observed-control-input-reference"
    elif result["observation_complete"]:
        result["status"] = "no-observed-control-input-reference"
    else:
        result["status"] = "control-input-observation-incomplete"
    return result


def summarize_events(events_file: Path, selected_cli: Path) -> dict[str, Any]:
    """Return compact observations from native or captured ``streaming-json``.

    This never scans free-form model text.  A ShipLoop CLI invocation is counted
    only when a structured stdout tool input has a recognized execution shape
    and an exact selected CLI path (or its resolved package-root equivalent).
    ``cli tool completed`` means a matching tool call received a ``completed``
    update. ``cli success observed`` means a terminal tool update explicitly
    reported exit code zero. Interim exit placeholders are ignored. Neither
    establishes ShipLoop compliance or product delivery.
    """
    event_path = _absolute(events_file)
    if not event_path.is_file():
        raise GrokAdapterError("event capture file must be an existing file")
    textual_paths, resolved_paths = _accepted_cli_paths(_absolute(selected_cli))

    known_types = {
        "text",
        "thought",
        "tool_call",
        "tool_call_update",
        "usage",
        "plan",
        "available_commands",
        "end",
        "error",
        "max_turns_reached",
    }
    event_types: Counter[str] = Counter()
    unknown_event_types: Counter[str] = Counter()
    invalid_json_lines: list[int] = []
    non_object_lines: list[int] = []
    availability_events = 0
    shiploop_routes: set[str] = set()
    matched_invocations: dict[str, str] = {}
    cli_invocations: list[tuple[str, list[str]]] = []
    update_statuses: defaultdict[str, list[str]] = defaultdict(list)
    update_exit_codes: defaultdict[str, list[int]] = defaultdict(list)
    end_stop_reasons: list[str] = []
    error_stop_reasons: list[str] = []
    usage_events = 0
    terminal_usage_observed = False
    actual_model_keys: set[str] = set()
    captured_receipts = 0
    ignored_stderr_receipts = 0

    for line_number, line in enumerate(event_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid_json_lines.append(line_number)
            continue
        if not isinstance(event, dict):
            non_object_lines.append(line_number)
            continue

        native_event, is_receipt = _captured_native_event(event)
        if is_receipt:
            captured_receipts += 1
            if event.get("stream") != "stdout":
                ignored_stderr_receipts += 1
        if native_event is None:
            continue
        event = native_event

        event_type = event.get("type")
        type_name = event_type if isinstance(event_type, str) and event_type else "<missing>"
        event_types[type_name] += 1
        if type_name not in known_types:
            unknown_event_types[type_name] += 1

        if type_name == "available_commands":
            availability_events += 1
            commands = event.get("commands")
            if isinstance(commands, list):
                for command in commands:
                    route = _shiploop_command_route(command)
                    if route is not None:
                        shiploop_routes.add(route)

        if type_name in {"tool_call", "tool_call_update"}:
            call_id = _call_id(event, line_number)
            for argv_tail in _cli_invocations(event, textual_paths, resolved_paths):
                cli_invocations.append((call_id, argv_tail))
                matched_invocations.setdefault(call_id, argv_tail[0] if argv_tail else "")
            if type_name == "tool_call_update" and isinstance(event.get("status"), str):
                update_statuses[call_id].append(event["status"])
            if type_name == "tool_call_update":
                exit_code = _reported_exit_code(event)
                if exit_code is not None:
                    update_exit_codes[call_id].append(exit_code)

        if type_name == "usage" and isinstance(event.get("usage"), dict):
            usage_events += 1
        if type_name == "end":
            if isinstance(event.get("stopReason"), str):
                end_stop_reasons.append(event["stopReason"])
            terminal_usage_observed = terminal_usage_observed or isinstance(event.get("usage"), dict)
        if type_name == "error" and isinstance(event.get("stopReason"), str):
            error_stop_reasons.append(event["stopReason"])

        model_usage = event.get("modelUsage")
        if isinstance(model_usage, dict):
            actual_model_keys.update(key for key in model_usage if isinstance(key, str) and key)

    invocation_ids = sorted(matched_invocations)
    completion_statuses: Counter[str] = Counter()
    completed_call_ids: list[str] = []
    completion_call_ids: list[str] = []
    exit_code_call_ids: list[str] = []
    zero_exit_code_call_ids: list[str] = []
    nonzero_exit_code_call_ids: list[str] = []
    matched_exit_codes: dict[str, list[int]] = {}
    for call_id in invocation_ids:
        statuses = update_statuses.get(call_id, [])
        if statuses:
            completion_call_ids.append(call_id)
        for status in statuses:
            completion_statuses[status] += 1
        if any(status.lower() == "completed" for status in statuses):
            completed_call_ids.append(call_id)
        exit_codes = update_exit_codes.get(call_id, [])
        if exit_codes:
            matched_exit_codes[call_id] = list(exit_codes)
            exit_code_call_ids.append(call_id)
            if any(code == 0 for code in exit_codes):
                zero_exit_code_call_ids.append(call_id)
            if any(code != 0 for code in exit_codes):
                nonzero_exit_code_call_ids.append(call_id)

    terminal_end_observed = event_types["end"] > 0
    terminal_error_observed = event_types["error"] > 0
    tool_invocation_observed = bool(invocation_ids)
    tool_completion_observed = bool(completion_call_ids)
    tool_completion_completed = bool(completed_call_ids)
    cli_exit_code_observed = bool(exit_code_call_ids)
    cli_success_observed = bool(zero_exit_code_call_ids)
    usage_observed = usage_events > 0 or terminal_usage_observed
    unqualified_shiploop_command = bool(shiploop_routes & {"/shiploop", SHIPLOOP_SKILL_NAME})
    qualified_shiploop_command = any(route not in {"/shiploop", SHIPLOOP_SKILL_NAME} for route in shiploop_routes)
    cli_calls = [
        {
            "call_id": call_id,
            "argv_tail": list(argv_tail),
            "completed": call_id in completed_call_ids,
            "exit_codes": list(update_exit_codes.get(call_id, [])),
        }
        for call_id, argv_tail in cli_invocations
    ]

    return {
        "event_count": sum(event_types.values()),
        "event_types": dict(sorted(event_types.items())),
        "invalid_json_lines": invalid_json_lines,
        "non_object_lines": non_object_lines,
        "unknown_event_types": dict(sorted(unknown_event_types.items())),
        "availability": {
            "observed": availability_events > 0,
            "shiploop_command_observed": unqualified_shiploop_command,
            "qualified_shiploop_command_observed": qualified_shiploop_command,
            "shiploop_routes": sorted(shiploop_routes),
            "event_count": availability_events,
        },
        "tool_invocation": {
            "observed": tool_invocation_observed,
            "count": len(invocation_ids),
            "call_ids": invocation_ids,
            "subcommands": {call_id: matched_invocations[call_id] for call_id in invocation_ids},
        },
        "tool_completion": {
            "observed": tool_completion_observed,
            "completed": tool_completion_completed,
            "cli_tool_completed": tool_completion_completed,
            "cli_exit_code_observed": cli_exit_code_observed,
            "cli_success_observed": cli_success_observed,
            "call_ids": completion_call_ids,
            "completed_call_ids": completed_call_ids,
            "statuses": dict(sorted(completion_statuses.items())),
            "exit_codes": {call_id: matched_exit_codes[call_id] for call_id in exit_code_call_ids},
            "zero_exit_code_call_ids": zero_exit_code_call_ids,
            "nonzero_exit_code_call_ids": nonzero_exit_code_call_ids,
        },
        "terminal": {
            "end_observed": terminal_end_observed,
            "error_observed": terminal_error_observed,
            "end_stop_reasons": end_stop_reasons,
            "error_stop_reasons": error_stop_reasons,
        },
        "usage": {
            "observed": usage_observed,
            "event_count": usage_events,
            "terminal_usage_observed": terminal_usage_observed,
        },
        "actual_model_keys": sorted(actual_model_keys),
        "cli_calls": cli_calls,
        "capture_receipts": {
            "observed": captured_receipts > 0,
            "count": captured_receipts,
            "ignored_stderr_count": ignored_stderr_receipts,
        },
        "available_commands_observed": availability_events > 0,
        "shiploop_command_observed": unqualified_shiploop_command,
        "qualified_shiploop_command_observed": qualified_shiploop_command,
        "cli_invocation_observed": tool_invocation_observed,
        "tool_completion_observed": tool_completion_observed,
        "tool_completion_completed": tool_completion_completed,
        "shiploop_cli_completed": tool_completion_completed,
        "shiploop_cli_exit_code_observed": cli_exit_code_observed,
        "shiploop_cli_success_observed": cli_success_observed,
        "terminal_end_observed": terminal_end_observed,
        "usage_observed": usage_observed,
    }
