"""Path vocabulary shared by the coordinator and delivery boundary.

Filesystem locations use pathlib. Repository paths are serialized Git names:
their slash separator is part of the protocol, never the host's os.sep.
"""
from pathlib import Path, PureWindowsPath
from typing import Any


GIT_PATH_SEPARATOR = "/"
ROOT_CONTROL_FILES = frozenset({".gitignore", ".claspignore"})
SKILL_CARD_NAME = "SKILL.md"
RUN_RECORD_NAME = "run.json"
RESULT_RECORD_NAME = "result.json"
ATTEMPT_RECORD_NAME = "attempt.json"
OPERATION_LOCK_NAME = "operation.lock"
DELIVERY_DIRECTORY = "delivery"
ASK_AGENT_TASK_SCRIPT = Path("scripts") / "ask_agent_task.py"
ASK_AGENT_WORKSPACE_SCRIPT = Path("scripts") / "ask_agent_workspace.py"
DISPATCHER_SCRIPT = Path("scripts") / "dispatch.js"


def is_git_relative_path(value: Any, *, directory: bool = False) -> bool:
    """Check raw components before pathlib can normalize away ambiguous input.

    Actual Git filenames can contain backslashes, colons, globs and newlines
    on the supported POSIX hosts. This is intentionally broader than a scope.
    """
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    relative = value[:-1] if directory and value.endswith(GIT_PATH_SEPARATOR) else value
    return all(part not in {"", ".", ".."} for part in relative.split(GIT_PATH_SEPARATOR))


def is_write_scope(value: Any) -> bool:
    """Accept one canonical exact path or directory prefix, without guessing OS."""
    return (is_git_relative_path(value, directory=True)
            and not PureWindowsPath(value).drive
            and not any(char in value for char in "\\*?[]")
            and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def scope_contains(scope: str, path: str) -> bool:
    """Compare validated Git paths at component boundaries, not string prefixes."""
    prefix = scope.removesuffix(GIT_PATH_SEPARATOR)
    return path == prefix or path.startswith(prefix + GIT_PATH_SEPARATOR)


def scopes_overlap(left: str, right: str) -> bool:
    """A directory and its child share ownership even without a trailing slash."""
    left = left.removesuffix(GIT_PATH_SEPARATOR)
    right = right.removesuffix(GIT_PATH_SEPARATOR)
    return scope_contains(left, right) or scope_contains(right, left)
