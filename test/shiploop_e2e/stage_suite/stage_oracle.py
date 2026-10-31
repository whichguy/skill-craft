#!/usr/bin/env python3
"""The stage suite's check engine (docs/plans/shiploop-stage-suite.md, "The oracle"): script-only checks over one stage
output, each tied to a planted condition (``P<n>``) or a control (``C<n>``) it ``proves``.

It sits below the harness's top level, so it is in neither the evaluator digest (boundary.evaluator_files reads the top
level only) nor the qualification snapshot. It reads a ``Bundle`` and writes nothing into it: a ``command`` runs in a
scratch copy of the tree that is removed afterwards, and that is the only thing this module creates.

A check is a dict with one kind key, an optional ``proves`` (an id) and an optional ``why`` (prose, never read):

    {"outcome": ["done", ...]}
    {"field": "failed_expectations[*].route", "equals": "check"}        equals | matches | exists | count | none_equal
    {"file": "src/paginate.js", "exists": true}                         exists | contains | not_contains | unchanged
    {"changed_only": ["src/strings.js", "docs/**"]}
    {"command": "node --test", "exit": 0}                               exit: a status, or "nonzero"
    {"stand_in": "stand_ins/empty", "command": "node --test", "kills": true}
    {"trace": "refusals_max", "value": 1}
    {"packet_contains": "re"}  {"packet_not_contains": "re"}  {"packet_head_contains": "re"}
    {"packet_issued": true}  {"settled_by_script": true}  {"current_stage": "implement"}

Rules the checks keep (each is pinned by test/shiploop-e2e-stage-oracle.test.py):
- A check that cannot be evaluated fails with the reason in ``detail``; ``run_check`` never raises on bad data. A missing
  input (no tree, no packet, no result) fails every check that needs it, ``*_not_contains`` and ``exists: false`` of a
  file included: an absence of evidence is not evidence of absence.
- ``file`` and ``changed_only`` compare the tree with the seed tree, by relative posix path: the bytes of a file and its
  executable bit, the target of a symlink. A folder holds no entry of its own, so an empty folder, added or removed, is not a
  change (a git-visible tree does not hold one either). They skip ``__pycache__`` folders, ``*.pyc`` files and the tree's
  top-level ``.git`` (version-control metadata, not a change). A path that resolves outside its tree (``..``, an absolute
  path, a symlink that leaves it) fails the check and is never read; a symlink met while walking a folder is compared by its
  target and never followed. The last component of a ``file`` path is looked at as it is: ``exists`` is true for a link that
  dangles, and ``unchanged`` of a link is its target string (a file replaced by a link to the same bytes is a change). A fifo,
  socket or device node is an entry of its own (neither read nor copied): added or removed, it is a change for ``unchanged`` as
  for ``changed_only``.
- ``command`` and ``stand_in`` run ``/bin/sh -c`` in a scratch COPY of the tree (regular files only, no ``.git``; a symlink is kept as a link only
  when its target stays inside the copy, any other is left out so that a command cannot write through it into the tree, the
  seed or the scenario), stdin closed, in a session of their own whose group is killed at the timeout (default 120 s) and again
  when the command ends, with the environment cut to PATH, HOME and TMPDIR (scratch folders), LC_ALL=C and
  SHIPLOOP_PROGRESS=off. A timeout fails the check whatever exit was asked for, and so does "nonzero" when the status is 126
  or 127 (the shell could not run the command, which says nothing about the code under test). Output goes to an unnamed file
  and the command is stopped, and the check fails like a timeout, once it has written more than OUTPUT_LIMIT bytes. The detail
  keeps the tail of the output. A process that leaves the session itself (``setsid``) is out of the group's reach and is not
  killed; that is a limit of this engine and not a promise.
- A ``stand_in`` with ``kills: true`` first runs its command on the candidate itself and needs it to pass there: a command
  that already fails on the candidate (a broken test, a missing module) kills every stand-in and says nothing about the
  tests' strength. That doubles the time a slow command takes, at most twice its timeout.
- ``[*]`` selects every element of a list; a key that is not there selects nothing (it is not an error). All selected
  values must satisfy an ``equals`` / ``matches`` / ``none_equal`` unless the check says ``any: true``, and at least one
  value must be selected, except with ``exists: false`` or ``count: 0``.
- Regular expressions are searched with re.MULTILINE and compiled once per check. Nothing guards a pathological pattern
  except the timeout of a command.

A sample's verdict (``verdict``): an id is caught (planted) or held (control) when at least one check proves it and every
check that proves it passes; an id no check in the list names is ``None``, not exercised, never a pass. The sample passes
when every exercised id is caught or held, no check without ``proves`` failed, and at least one check ran.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_trace  # noqa: E402  (shiploop_trace.refused: the one definition of a refusal)

COMMAND_SECONDS = 120.0  # a command's ceiling unless the check says "timeout"
TAIL = 1500  # bytes of a command's output the detail keeps
OUTPUT_LIMIT = 16 * 1024 * 1024  # bytes a command may write before it is stopped as a flood
POLL = 0.05  # seconds between looks at a running command's output size
DETAIL = 400  # characters of any one value a detail quotes
UNRUNNABLE = (126, 127)  # the shell's "cannot execute" and "not found": never a test failing
SHELL = "/bin/sh"

# kind key -> the keys it takes besides "proves" and "why"
KINDS: dict[str, tuple[str, ...]] = {
    "outcome": (),
    "field": ("equals", "matches", "exists", "count", "none_equal", "any"),
    "file": ("exists", "contains", "not_contains", "unchanged"),
    "changed_only": (),
    "command": ("exit", "timeout"),
    "stand_in": ("command", "kills", "timeout"),
    "trace": ("value",),
    "packet_contains": (),
    "packet_not_contains": (),
    "packet_head_contains": (),
    "packet_issued": (),
    "settled_by_script": (),
    "current_stage": (),
}
COMMON = ("proves", "why")
FIELD_ASSERTIONS = ("equals", "matches", "exists", "count", "none_equal")
FILE_ASSERTIONS = ("exists", "contains", "not_contains", "unchanged")
TRACE_KINDS = ("refusals_max",)
SEGMENT = re.compile(r"^([^.\[\]]*)((?:\[\*\])*)$")


@dataclass
class Bundle:
    """What a check reads: one stage's output. Every field has a default, so a bundle for one tier carries only its inputs.

    ``tree`` is the candidate tree after the stage, ``seed_tree`` the tree at the seed point; ``result`` the accepted (or
    parked) result; ``trace`` the rows of the run's trace.jsonl (None: not read, which is not the same as no rows);
    ``packet`` the packet file's text and ``packet_head`` what ``shiploop next`` printed; ``issued`` whether a packet was
    issued; ``settled`` whether the stage was recorded done by script; ``scenario_dir`` the scenario folder, which a
    ``stand_in`` overlay is relative to.
    """
    result: dict | None = None
    tree: Path | None = None
    seed_tree: Path | None = None
    run_dir: Path | None = None
    trace: list | None = None
    packet: str | None = None
    packet_head: str | None = None
    issued: bool = False
    settled: bool = False
    current_stage: str | None = None
    scenario_dir: Path | None = None

    @property
    def knowledge(self) -> Path | None:
        """The knowledge home in the candidate tree (docs/shiploop)."""
        return None if self.tree is None else Path(self.tree) / "docs" / "shiploop"

    @property
    def notes(self) -> Path | None:
        """RUN/notes."""
        return None if self.run_dir is None else Path(self.run_dir) / "notes"

    @property
    def records(self) -> Path | None:
        """RUN itself, which holds the expectations/, tests/ and loops/ records."""
        return None if self.run_dir is None else Path(self.run_dir)


class Fail(Exception):
    """A check that is evaluated and does not hold, or cannot be: the message is its detail."""


# --------------------------------------------------------------------------------------------------------- validation

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def _regex(value: Any, label: str, problems: list[str]) -> None:
    if not _is_text(value):
        problems.append(f"{label} must be a non-empty regular expression string")
        return
    try:
        re.compile(value, re.MULTILINE)
    except (re.error, RecursionError, OverflowError) as error:
        problems.append(f"{label} is not a regular expression: {error}")


def _path_problem(path: Any) -> str | None:
    """Why `path` cannot name something inside a tree, or None. A relative posix path without '..'."""
    if not _is_text(path):
        return "must be a non-empty string"
    if "\0" in path:
        return "holds a NUL"
    if path.startswith("/"):
        return "is absolute"
    if ".." in path.split("/"):
        return "climbs out with '..'"
    return None


def _parts(path: str) -> list[str]:
    return [part for part in path.split("/") if part not in ("", ".")]


def _glob_problem(pattern: Any) -> str | None:
    problem = _path_problem(pattern)
    if problem:
        return problem
    if pattern.endswith("/"):
        return "ends with '/': write dir/** for everything below dir"
    if any(char in pattern for char in "[]{}"):
        return "uses a bracket or brace, which a glob here does not (only * ** ?)"
    return None


def _field_segments(path: Any) -> list[tuple[str, int]] | str:
    """The (key, number of [*]) segments of a field path, or the reason it is malformed."""
    if not _is_text(path):
        return "must be a non-empty string"
    found = []
    for index, text in enumerate(path.split(".")):
        match = SEGMENT.match(text)
        if not match:
            return f"segment {text!r} is not a key followed by [*]"
        key, stars = match.group(1), len(match.group(2)) // 3
        if not key and (index or not stars):
            return f"segment {text!r} has no key"
        found.append((key, stars))
    return found


def _only_one(check: Mapping, names: Iterable[str], kind: str, problems: list[str]) -> str | None:
    present = [name for name in names if name in check]
    if len(present) != 1:
        problems.append(f"{kind} takes exactly one of {', '.join(names)}" +
                        (f" (got {', '.join(present)})" if present else " (got none)"))
        return None
    return present[0]


def _timeout_problem(check: Mapping, problems: list[str]) -> None:
    if "timeout" in check:
        value = check["timeout"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            problems.append("timeout must be a positive number of seconds")


def _kinds(check: Mapping) -> list[str]:
    """The kind keys a check holds. ``command`` beside ``stand_in`` is the stand-in's own command, not a second kind."""
    return [kind for kind in KINDS if kind in check and not (kind == "command" and "stand_in" in check)]


def _problems(check: Any, ids: frozenset | None) -> list[str]:
    if not isinstance(check, dict):
        return [f"a check must be an object, not {type(check).__name__}"]
    kinds = _kinds(check)
    if not kinds:
        return ["no check kind: one of " + ", ".join(KINDS) + " is required"]
    if len(kinds) > 1:
        return ["several check kinds in one check: " + ", ".join(kinds)]
    kind = kinds[0]
    problems = []
    allowed = {kind, *KINDS[kind], *COMMON}
    problems += [f"unknown key {key!r} for {kind}" for key in check if key not in allowed]
    if "proves" in check:
        if not _is_text(check["proves"]):
            problems.append("proves must be an id string")
        elif ids is not None and check["proves"] not in ids:
            problems.append(f"proves {check['proves']!r} is not a planted or control id of the scenario")
    if "why" in check and not isinstance(check["why"], str):
        problems.append("why must be a string")
    value = check[kind]
    if kind == "outcome":
        if not isinstance(value, list) or not value or not all(_is_text(item) for item in value):
            problems.append("outcome must be a non-empty list of outcome strings")
    elif kind == "field":
        segments = _field_segments(value)
        if isinstance(segments, str):
            problems.append(f"field {segments}")
        chosen = _only_one(check, FIELD_ASSERTIONS, "field", problems)
        if chosen == "matches":
            _regex(check["matches"], "matches", problems)
        elif chosen == "exists" and not isinstance(check["exists"], bool):
            problems.append("exists must be true or false")
        elif chosen == "count" and (not _is_int(check["count"]) or check["count"] < 0):
            problems.append("count must be a non-negative integer")
        if "any" in check:
            if not isinstance(check["any"], bool):
                problems.append("any must be true or false")
            elif chosen in ("exists", "count"):
                problems.append(f"any has no meaning with {chosen} (it applies to equals, matches and none_equal)")
    elif kind == "file":
        problem = _path_problem(value)
        if problem:
            problems.append(f"file path {problem}")
        chosen = _only_one(check, FILE_ASSERTIONS, "file", problems)
        if chosen in ("contains", "not_contains"):
            _regex(check[chosen], chosen, problems)
        elif chosen in ("exists", "unchanged") and not isinstance(check[chosen], bool):
            problems.append(f"{chosen} must be true or false")
    elif kind == "changed_only":
        if not isinstance(value, list):
            problems.append("changed_only must be a list of globs")
        else:
            for glob in value:
                problem = _glob_problem(glob)
                if problem:
                    problems.append(f"changed_only glob {glob!r} {problem}")
    elif kind in ("command", "stand_in"):
        if kind == "stand_in":
            problem = _path_problem(value)
            if problem:
                problems.append(f"stand_in path {problem}")
            if "command" not in check:
                problems.append("stand_in needs a command")
            if not isinstance(check.get("kills"), bool):
                problems.append("stand_in needs kills: true or false")
        command = check.get("command") if kind == "stand_in" else value
        if "command" in check and (not _is_text(command) or "\0" in command):
            problems.append("command must be a non-empty string")
        if kind == "command":
            wanted = check.get("exit", None)
            if "exit" not in check:
                problems.append('command needs exit: a status from 0 to 255, or "nonzero"')
            elif not (wanted == "nonzero" or (_is_int(wanted) and 0 <= wanted <= 255)):
                problems.append('exit must be a status from 0 to 255, or "nonzero"')
        _timeout_problem(check, problems)
    elif kind == "trace":
        if value not in TRACE_KINDS:
            problems.append("trace must be one of " + ", ".join(TRACE_KINDS))
        if "value" not in check:
            problems.append("trace needs a value")
        elif not _is_int(check["value"]) or check["value"] < 0:
            problems.append("trace value must be a non-negative integer")
    elif kind in ("packet_contains", "packet_not_contains", "packet_head_contains"):
        _regex(value, kind, problems)
    elif kind in ("packet_issued", "settled_by_script"):
        if not isinstance(value, bool):
            problems.append(f"{kind} must be true or false")
    elif kind == "current_stage":
        if not _is_text(value):
            problems.append("current_stage must be a stage name string")
    return problems


def validate_checks(checks: Any, ids: Iterable[str] | None) -> list[str]:
    """What is wrong with a list of checks, one sentence each; empty when it is valid. `ids` are the planted and control ids
    a ``proves`` may name (None skips that one test)."""
    if not isinstance(checks, list):
        return [f"checks must be a list, not {type(checks).__name__}"]
    known = None if ids is None else frozenset(ids)
    return [f"checks[{index}]: {problem}" for index, check in enumerate(checks) for problem in _problems(check, known)]


# ------------------------------------------------------------------------------------------------------------- trees

def _ignored(name: str, top: bool) -> bool:
    """Compiled files and caches are never part of a comparison; the top of a tree also holds version-control metadata."""
    return name == "__pycache__" or name.endswith(".pyc") or (top and name == ".git")


def _root(path: Path | None, label: str) -> str:
    if path is None:
        raise Fail(f"the bundle has no {label}")
    real = os.path.realpath(path)
    if not os.path.isdir(real):
        raise Fail(f"the {label} {path} is not a folder")
    return real


def _inside(root: str, path: str) -> str:
    """The real path of `path` below the real `root`, or a Fail: a path that leaves the tree is never read."""
    parts = _parts(path)
    if ".." in parts:
        raise Fail(f"{path!r} climbs out of the tree")
    real = os.path.realpath(os.path.join(root, *parts))
    if os.path.commonpath([root, real]) != root:
        raise Fail(f"{path!r} resolves outside the tree")
    return real


def _entry(root: str, path: str) -> str:
    """Where `path` is in the real `root`, its last component NOT resolved (a symlink there is the entry, not its target).
    The folders above it are resolved and must stay inside; a Fail when they leave."""
    parts = _parts(path)
    if not parts:
        return root
    return os.path.join(_inside(root, "/".join(parts[:-1])), parts[-1])


def _files(folder: str, top: bool) -> dict[str, tuple]:
    """{relative posix path: entry} for every file below `folder`. An entry is ("file", path, executable), ("link", target) (a
    symlink, never followed) or ("special",); folders hold no entry of their own."""
    found: dict[str, tuple] = {}
    stack = [("", folder, top)]
    while stack:
        rel, here, at_top = stack.pop()
        with os.scandir(here) as scan:
            entries = sorted(scan, key=lambda item: item.name)
        for item in entries:
            if _ignored(item.name, at_top):
                continue
            name = f"{rel}/{item.name}" if rel else item.name
            mode = item.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                found[name] = ("link", os.readlink(item.path))
            elif stat.S_ISDIR(mode):
                stack.append((name, item.path, False))
            elif stat.S_ISREG(mode):
                found[name] = ("file", item.path, bool(mode & stat.S_IXUSR))
            else:
                found[name] = ("special",)
    return found


def _state(entry: str, top: bool) -> dict[str, tuple]:
    """The entries at one path (its last component not resolved): a folder's files, a file, a symlink or any other kind of file
    (a fifo, a socket, a device node: ("special",), as `_files` records it) as {"": entry}, an absent path as {}."""
    if os.path.islink(entry):
        return {"": ("link", os.readlink(entry))}
    if os.path.isdir(entry):
        return _files(entry, top)
    if os.path.isfile(entry):
        return {"": ("file", entry, bool(os.stat(entry).st_mode & stat.S_IXUSR))}
    if os.path.lexists(entry):
        return {"": ("special",)}
    return {}


def _same_bytes(left: str, right: str) -> bool:
    """Whether two files hold the same bytes. Read here and not by filecmp, whose cache is keyed on size and mtime."""
    if os.path.getsize(left) != os.path.getsize(right):
        return False
    with open(left, "rb") as one, open(right, "rb") as other:
        while True:
            chunk = one.read(65536)
            if chunk != other.read(65536):
                return False
            if not chunk:
                return True


def _same(left: tuple, right: tuple) -> bool:
    if left[0] != right[0]:
        return False
    if left[0] == "link":
        return left[1] == right[1]
    if left[0] == "file":
        return left[2] == right[2] and _same_bytes(left[1], right[1])
    return True


def _diff(before: Mapping[str, tuple], after: Mapping[str, tuple]) -> list[str]:
    """The relative paths added, removed or changed (bytes) between two states."""
    return sorted(name for name in set(before) | set(after)
                  if name not in before or name not in after or not _same(before[name], after[name]))


def _some(names: list[str], limit: int = 6) -> str:
    return ", ".join(names[:limit]) + (f" (+{len(names) - limit} more)" if len(names) > limit else "")


def _clip(text: Any, limit: int = DETAIL) -> str:
    text = text if isinstance(text, str) else json.dumps(text, sort_keys=True, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "..."


def _glob(pattern: str) -> re.Pattern:
    """A glob as a regex over a relative posix path: ** crosses folders, * and ? stay inside one name."""
    pattern = "/".join(_parts(pattern))
    out, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(out) + r"\Z", re.DOTALL)


# ----------------------------------------------------------------------------------------------------------- commands

def _remove(path: Path) -> None:
    """Delete a scratch folder even when a command left a read-only folder in it. Symlinks are never chmod'ed (that would
    follow them out of the scratch)."""
    for here, folders, _ in os.walk(path):
        for name in ["", *folders]:
            full = os.path.join(here, name) if name else here
            if not os.path.islink(full):
                try:
                    os.chmod(full, 0o700)
                except OSError:
                    pass
    shutil.rmtree(path, ignore_errors=True)


def _export(tree: str, work: Path) -> None:
    """Copy `tree` (a real path) to `work`: compiled files, caches and the top-level .git left out, only regular files read (a
    fifo would block the copy), symlinks kept as links when their target stays inside `work` and left out otherwise (a link
    that leaves would let a command write into the tree, the seed tree or the scenario)."""
    def ignore(here: str, names: list[str]) -> list[str]:
        return [name for name in names if _ignored(name, here == tree)]

    def copy(source: str, target: str, *, follow_symlinks: bool = True) -> None:
        if stat.S_ISREG(os.lstat(source).st_mode):
            shutil.copy2(source, target)

    shutil.copytree(tree, work, symlinks=True, ignore=ignore, copy_function=copy)
    base = os.path.realpath(work)
    for here, folders, names in os.walk(work):
        for name in [*folders, *names]:
            full = os.path.join(here, name)
            if os.path.islink(full) and os.path.commonpath([base, os.path.realpath(full)]) != base:
                os.unlink(full)


def _overlay(source: str, work: Path) -> None:
    """Lay the files of `source` over `work`. A destination that is a symlink is replaced and never written through."""
    for here, folders, names in os.walk(source):
        rel = os.path.relpath(here, source)
        target = work if rel == "." else work / rel
        if os.path.islink(target):
            raise Fail(f"the overlay would write through the symlink {rel}")
        if os.path.lexists(target) and not os.path.isdir(target):
            os.unlink(target)
        target.mkdir(parents=True, exist_ok=True)
        for name in [*names, *[name for name in folders if os.path.islink(os.path.join(here, name))]]:
            origin, goal = os.path.join(here, name), target / name
            if os.path.lexists(goal):
                if os.path.isdir(goal) and not os.path.islink(goal):
                    shutil.rmtree(goal)
                else:
                    os.unlink(goal)
            if os.path.islink(origin):
                os.symlink(os.readlink(origin), goal)
            elif os.path.isfile(origin):
                shutil.copy2(origin, goal)


def _execute(command: str, cwd: Path, scratch: Path, seconds: float) -> dict:
    """Run `command` under /bin/sh in `cwd`: ``{returncode, timeout, flooded, tail}``. Standard input is closed, the command
    leads a session of its own whose group is killed at the timeout and again when the leader is done, and the environment
    holds PATH, HOME, TMPDIR, LC_ALL and SHIPLOOP_PROGRESS only. The output goes to an unnamed file, of which only the end is
    read; a command that writes more than OUTPUT_LIMIT bytes is killed (``flooded``)."""
    home, temp = scratch / "home", scratch / "tmp"
    home.mkdir(exist_ok=True)
    temp.mkdir(exist_ok=True)
    env = {"PATH": os.environ.get("PATH") or os.defpath, "HOME": str(home), "TMPDIR": str(temp), "LC_ALL": "C",
           "SHIPLOOP_PROGRESS": "off"}
    with tempfile.TemporaryFile() as log:
        try:
            proc = subprocess.Popen([SHELL, "-c", command], cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            return {"returncode": None, "timeout": False, "flooded": False, "tail": f"could not start {SHELL}: {error}"}
        timed_out = flooded = False
        end = time.monotonic() + seconds
        try:
            while True:
                try:
                    proc.wait(timeout=max(0.0, min(POLL, end - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    pass
                if os.fstat(log.fileno()).st_size > OUTPUT_LIMIT:
                    flooded = True
                    break
                if time.monotonic() >= end:
                    timed_out = True
                    break
        finally:
            try:  # the group of a leader that is gone too: whatever the command started and left behind
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
        size = os.fstat(log.fileno()).st_size
        flooded = flooded or size > OUTPUT_LIMIT
        log.seek(max(0, size - TAIL))
        data = log.read(TAIL)
    return {"returncode": proc.returncode, "timeout": timed_out, "flooded": flooded,
            "tail": data.decode("utf-8", "replace").strip()}


def _in_copy(bundle: Bundle, command: str, seconds: float, overlay: str | None) -> dict:
    """Run `command` in a scratch export of the bundle's tree, with `overlay` (a folder of the scenario) laid over it."""
    tree = _root(bundle.tree, "tree")
    source = None
    if overlay is not None:
        base = _root(bundle.scenario_dir, "scenario folder")
        source = _inside(base, overlay)
        if not os.path.isdir(source):
            raise Fail(f"the stand-in folder {overlay!r} is not a folder of the scenario")
    scratch = Path(tempfile.mkdtemp(prefix="stage-oracle-"))
    try:
        work = scratch / "tree"
        _export(tree, work)
        if source is not None:
            _overlay(source, work)
        return _execute(command, work, scratch, seconds)
    finally:
        _remove(scratch)


def _ran(done: dict) -> str:
    head = ("timed out" if done["timeout"] else
            f"stopped after more than {OUTPUT_LIMIT // (1024 * 1024)} MB of output" if done["flooded"] else
            f"exit {done['returncode']}")
    return head + (": " + _clip(done["tail"], TAIL) if done["tail"] else "")


def _failed(done: dict) -> bool | None:
    """Whether a finished command failed in the sense of "nonzero"; None when it says nothing about the code (it timed out or
    flooded its output, could not start, or the shell could not run it)."""
    if done["timeout"] or done["flooded"] or done["returncode"] is None or done["returncode"] in UNRUNNABLE:
        return None
    return done["returncode"] != 0


# ------------------------------------------------------------------------------------------------------------- checks

def _equal(left: Any, right: Any) -> bool:
    """JSON equality: a boolean is never a number, 1 equals 1.0, containers compare by content."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    return type(left) is type(right) and left == right


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _select(root: Any, segments: list[tuple[str, int]]) -> list:
    """The values a field path selects; a key that is not there, and a [*] over something that is not a list, select nothing."""
    current = [root]
    for key, stars in segments:
        following = []
        for value in current:
            if key:
                if not (isinstance(value, dict) and key in value):
                    continue
                value = value[key]
            level = [value]
            for _ in range(stars):
                level = [item for each in level if isinstance(each, list) for item in each]
            following += level
        current = following
    return current


def _outcome(check: dict, bundle: Bundle) -> str:
    if not isinstance(bundle.result, dict):
        raise Fail("the bundle has no result")
    got = bundle.result.get("outcome")
    if not isinstance(got, str) or got not in check["outcome"]:
        raise Fail(f"outcome {_clip(got)} is not one of {', '.join(check['outcome'])}")
    return f"outcome {got}"


def _field(check: dict, bundle: Bundle) -> str:
    if not isinstance(bundle.result, dict):
        raise Fail("the bundle has no result")
    path = check["field"]
    values = _select(bundle.result, _field_segments(path))
    if "exists" in check:
        if bool(values) != check["exists"]:
            raise Fail(f"{path} selects {len(values)} values; exists: {str(check['exists']).lower()} was asked")
        return f"{path} {'exists' if values else 'is absent'}"
    if "count" in check:
        if len(values) != check["count"]:
            raise Fail(f"{path} selects {len(values)} values, not {check['count']}")
        return f"{path} selects {len(values)} values"
    if not values:
        raise Fail(f"{path} selects no value")
    if "equals" in check:
        verb, test = "equal", lambda value: _equal(value, check["equals"])
        wanted = check["equals"]
    elif "none_equal" in check:
        verb, test = "differ from", lambda value: not _equal(value, check["none_equal"])
        wanted = check["none_equal"]
    else:
        pattern = re.compile(check["matches"], re.MULTILINE)
        verb, test, wanted = "match", lambda value: bool(pattern.search(_text(value))), check["matches"]
    bad = [value for value in values if not test(value)]
    enough = len(bad) < len(values) if check.get("any") else not bad
    if not enough:
        raise Fail(f"{path}: {len(bad)} of {len(values)} values do not {verb} {_clip(wanted)}: {_clip(bad)}")
    return f"{path}: {len(values) - len(bad)} of {len(values)} values {verb} {_clip(wanted)}"


def _file(check: dict, bundle: Bundle) -> str:
    path = check["file"]
    tree = _root(bundle.tree, "tree")
    real = _inside(tree, path)
    if "exists" in check:
        there = os.path.lexists(_entry(tree, path))
        if there != check["exists"]:
            raise Fail(f"{path} {'is there' if there else 'is not there'}")
        return f"{path} {'is there' if there else 'is not there'}"
    if "unchanged" in check:
        seed = _root(bundle.seed_tree, "seed tree")
        top = not _parts(path)
        _inside(seed, path)  # a seed path that leaves the seed tree fails, as the tree's does
        changed = _diff(_state(_entry(seed, path), top), _state(_entry(tree, path), top))
        if (not changed) != check["unchanged"]:
            raise Fail(f"{path} is {'changed' if changed else 'unchanged'} against the seed tree" +
                       (f": {_some([f'{path}/{name}' if name else path for name in changed])}" if changed else ""))
        return f"{path} is {'changed' if changed else 'unchanged'}"
    if not os.path.isfile(real):
        raise Fail(f"{path} is not a file in the tree" + (" (a folder)" if os.path.isdir(real) else ""))
    with open(real, "rb") as handle:
        text = handle.read().decode("utf-8", "replace")
    wanted = check.get("contains", check.get("not_contains"))
    found = re.compile(wanted, re.MULTILINE).search(text)
    if "contains" in check and not found:
        raise Fail(f"{path} does not match /{wanted}/")
    if "not_contains" in check and found:
        raise Fail(f"{path} matches /{wanted}/: {_clip(found.group(0), 120)}")
    return f"{path} {'matches' if found else 'does not match'} /{wanted}/"


def _changed_only(check: dict, bundle: Bundle) -> str:
    tree, seed = _root(bundle.tree, "tree"), _root(bundle.seed_tree, "seed tree")
    allowed = [_glob(glob) for glob in check["changed_only"]]
    changed = _diff(_files(seed, True), _files(tree, True))
    outside = [name for name in changed if not any(pattern.match(name) for pattern in allowed)]
    if outside:
        raise Fail(f"{len(outside)} of {len(changed)} changed files are outside {check['changed_only']}: {_some(outside)}")
    return f"{len(changed)} changed files, all inside {check['changed_only']}"


def _command(check: dict, bundle: Bundle) -> str:
    done = _in_copy(bundle, check["command"], check.get("timeout", COMMAND_SECONDS), None)
    wanted = check["exit"]
    if done["timeout"] or done["flooded"] or done["returncode"] is None:
        raise Fail(_ran(done))
    if wanted == "nonzero":
        if done["returncode"] in UNRUNNABLE:
            raise Fail(f"the shell could not run the command ({_ran(done)})")
        if done["returncode"] == 0:
            raise Fail(f"exit 0, a nonzero status was asked for: {_clip(done['tail'], TAIL)}")
    elif done["returncode"] != wanted:
        raise Fail(f"{_ran(done)} (exit {wanted} was asked for)")
    return _ran(done)


def _stand_in(check: dict, bundle: Bundle) -> str:
    seconds = check.get("timeout", COMMAND_SECONDS)
    if check["kills"]:  # a command that fails on the candidate itself kills every stand-in and shows nothing
        base = _in_copy(bundle, check["command"], seconds, None)
        if _failed(base) is None:
            raise Fail(f"the command said nothing about the stand-in: it gave no verdict on the candidate itself ({_ran(base)})")
        if _failed(base):
            raise Fail(f"the command fails on the candidate itself, so its failure on the stand-in {check['stand_in']!r} shows "
                       f"nothing ({_ran(base)})")
    done = _in_copy(bundle, check["command"], seconds, check["stand_in"])
    failed = _failed(done)
    if failed is None:
        raise Fail(f"the command said nothing about the stand-in ({_ran(done)})")
    if failed != check["kills"]:
        raise Fail(f"the stand-in {check['stand_in']!r} {'survived' if not failed else 'was killed'}: {_ran(done)}")
    return f"the stand-in {check['stand_in']!r} {'was killed' if failed else 'survived'}: {_ran(done)}"


def _trace(check: dict, bundle: Bundle) -> str:
    if not isinstance(bundle.trace, list):
        raise Fail("the bundle has no trace")
    refusals = sum(1 for row in bundle.trace if isinstance(row, Mapping) and shiploop_trace.refused(row))
    if refusals > check["value"]:
        raise Fail(f"{refusals} refusals, at most {check['value']} allowed")
    return f"{refusals} refusals, at most {check['value']} allowed"


def _packet(attribute: str, label: str, absent: bool) -> Callable[[dict, Bundle], str]:
    kind = "packet_not_contains" if absent else ("packet_head_contains" if attribute == "packet_head" else "packet_contains")

    def run(check: dict, bundle: Bundle) -> str:
        text = getattr(bundle, attribute)
        if not isinstance(text, str):
            raise Fail(f"the bundle has no {label}")
        pattern = check[kind]
        found = re.compile(pattern, re.MULTILINE).search(text)
        if bool(found) == absent:
            raise Fail(f"the {label} {'matches' if found else 'does not match'} /{pattern}/" +
                       (f": {_clip(found.group(0), 120)}" if found else ""))
        return f"the {label} {'matches' if found else 'does not match'} /{pattern}/"
    return run


def _flag(attribute: str, kind: str) -> Callable[[dict, Bundle], str]:
    def run(check: dict, bundle: Bundle) -> str:
        got = bool(getattr(bundle, attribute))
        if got != check[kind]:
            raise Fail(f"{attribute} is {got}, not {check[kind]}")
        return f"{attribute} is {got}"
    return run


def _stage(check: dict, bundle: Bundle) -> str:
    if bundle.current_stage != check["current_stage"]:
        raise Fail(f"the run is at {bundle.current_stage}, not {check['current_stage']}")
    return f"the run is at {bundle.current_stage}"


RUNNERS: dict[str, Callable[[dict, Bundle], str]] = {
    "outcome": _outcome, "field": _field, "file": _file, "changed_only": _changed_only, "command": _command,
    "stand_in": _stand_in, "trace": _trace,
    "packet_contains": _packet("packet", "packet", False), "packet_not_contains": _packet("packet", "packet", True),
    "packet_head_contains": _packet("packet_head", "packet head", False),
    "packet_issued": _flag("issued", "packet_issued"), "settled_by_script": _flag("settled", "settled_by_script"),
    "current_stage": _stage,
}


def run_check(check: Any, bundle: Bundle) -> dict:
    """``{proves, kind, pass, detail}`` for one check. A check that is malformed, or cannot be evaluated, fails with the
    reason in ``detail``; nothing raises. ``proves`` is read even from a malformed check, so it fails the id it names."""
    proves = check.get("proves") if isinstance(check, dict) and isinstance(check.get("proves"), str) else None
    kind = "invalid"
    try:
        problems = _problems(check, None)
        if problems:
            raise Fail("invalid check: " + "; ".join(problems))
        kind = _kinds(check)[0]
        detail = RUNNERS[kind](check, bundle)
        return {"proves": proves, "kind": kind, "pass": True, "detail": detail}
    except Fail as failure:
        return {"proves": proves, "kind": kind, "pass": False, "detail": str(failure)}
    except Exception as error:  # noqa: BLE001 - a record, never a crash of the harness: the check failed
        return {"proves": proves, "kind": kind, "pass": False,
                "detail": f"the check could not be evaluated: {type(error).__name__}: {_clip(str(error))}"}


def run_checks(checks: Any, bundle: Bundle) -> list[dict]:
    """``run_check`` over a list, in order. Something that is not a list is one failed check."""
    if not isinstance(checks, list):
        return [{"proves": None, "kind": "invalid", "pass": False,
                 "detail": f"invalid check: checks must be a list, not {type(checks).__name__}"}]
    return [run_check(check, bundle) for check in checks]


def verdict(planted_ids: Iterable[str] | None, control_ids: Iterable[str] | None, results: Iterable[dict] | None) -> dict:
    """The sample's verdict over the results of the checks that ran: ``caught`` (per planted id) and ``held`` (per control
    id) are True (every check that proves it passed), False (one failed) or None (no check ran for it: not exercised, never
    a pass); ``unproved_failures`` are the failed checks that prove no known id; ``pass`` needs a check to have run, no False
    and no unproved failure; ``checks`` counts what ran."""
    rows = [row if isinstance(row, dict) else {"proves": None, "kind": "invalid", "pass": False,
                                                "detail": f"malformed result {_clip(row)}"} for row in results or []]
    planted, controls = list(planted_ids or []), list(control_ids or [])

    def settle(ids: list[str]) -> dict[str, bool | None]:
        found = {}
        for ident in ids:
            proving = [row for row in rows if row.get("proves") == ident]
            found[ident] = all(row.get("pass") is True for row in proving) if proving else None
        return found

    caught, held = settle(planted), settle(controls)
    known = {*planted, *controls}
    unproved = [f"{row.get('kind')}: {row.get('detail')}" for row in rows
                if row.get("pass") is not True and not (isinstance(row.get("proves"), str) and row["proves"] in known)]
    return {"caught": caught, "held": held, "unproved_failures": unproved, "checks": len(rows),
            "pass": bool(rows) and False not in caught.values() and False not in held.values() and not unproved}
