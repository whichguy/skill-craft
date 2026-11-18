"""The Python floor of ShipLoop's scripts, checked before anything else is imported.

``FLOOR`` is the oldest Python the scripts' code runs on, not a support policy: the library modules subscript
``os.PathLike`` and call ``str.removeprefix`` (Python 3.9), and need nothing newer (owner, 2026-11-18: no artificial
mandates).  Every entry script imports this module first and calls ``require``.  Only syntax and calls that Python 3.7
accepts belong here, so an older interpreter reaches this code instead of a ``TypeError`` from a later import.

An interpreter below the floor is not a reason to fail when a newer one is installed: ``require`` then runs the same
script again with the newest Python on PATH that meets the floor (``python3``, ``python3.N``), and refuses only when
there is none.
"""

import os
import subprocess
import sys

FLOOR = (3, 9)
# Set for the one run again, so an interpreter that answered the version query with a version it does not have cannot
# make the script run itself again and again; cleared as soon as an interpreter at the floor is running.
REEXEC_MARK = "SHIPLOOP_PYTHON_REEXEC"
VERSION_QUERY = "import sys; print('%d %d' % tuple(sys.version_info[:2]))"


def _version(path):
    """(major, minor) of the interpreter at ``path``, or None when it does not answer."""
    try:
        done = subprocess.run([path, "-c", VERSION_QUERY], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, universal_newlines=True, timeout=10, check=False)
        major, minor = done.stdout.split()
        return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def candidates():
    """Every ``python3`` and ``python3.N`` executable on PATH, in PATH order, each real file once."""
    found, seen = [], set()
    for folder in os.environ.get("PATH", os.defpath).split(os.pathsep):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if name != "python3" and not (name.startswith("python3.") and name[len("python3."):].isdigit()):
                continue
            path = os.path.join(folder, name)
            real = os.path.realpath(path)
            if real in seen or os.path.isdir(path) or not os.access(path, os.X_OK):
                continue
            seen.add(real)
            found.append(path)
    return found


def newest():
    """(version, path) of the newest interpreter on PATH that meets the floor, the first one on PATH among equals; or None.

    Two kinds are never asked, which saves a process start on every hook event: the interpreter running this check (it
    is below the floor) and a ``python3.N`` whose name is below the floor.
    """
    running = os.path.realpath(sys.executable) if sys.executable else None
    best = None
    for path in candidates():
        name = os.path.basename(path)
        if name != "python3" and (3, int(name[len("python3."):])) < FLOOR:
            continue
        if os.path.realpath(path) == running:
            continue
        version = _version(path)
        if version is not None and version >= FLOOR and (best is None or version > best[0]):
            best = (version, path)
    return best


def _flags():
    """The interpreter options that change how a script runs, so the run again keeps them."""
    if sys.flags.isolated:
        return ["-I"] + (["-B"] if sys.flags.dont_write_bytecode else [])
    flags = []
    for option, on in (("-E", sys.flags.ignore_environment), ("-s", sys.flags.no_user_site), ("-B", sys.flags.dont_write_bytecode)):
        if on:
            flags.append(option)
    return flags


def require(hook_event=False):
    """Return on Python ``FLOOR`` or newer.  Below it, run this script again with the newest Python on PATH that meets the
    floor; when there is none, exit 2 with one line, or exit 0 silently for a host hook event.

    A hook event runs on every tool call of every project, so with no Python at the floor it does nothing rather than
    print an error each time; the keepalive is simply absent.  The CLI states the requirement instead.
    """
    if sys.version_info >= FLOOR:
        os.environ.pop(REEXEC_MARK, None)  # the children of a script run again may pick their own interpreter
        return
    if os.environ.get(REEXEC_MARK):
        reason = "ShipLoop started it as the newest Python on PATH (%s is set), so it looks no further" % REEXEC_MARK
    else:
        found = newest()
        if found is None:
            reason = "no python3 or python3.N on PATH is %d.%d or newer; install one or put it on PATH" % FLOOR
        else:
            os.environ[REEXEC_MARK] = "1"
            try:
                os.execv(found[1], [found[1]] + _flags() + sys.argv)
            except OSError as exc:
                reason = "running %s failed: %s" % (found[1], exc)
    if not hook_event:
        sys.stderr.write("error: ShipLoop needs Python %d.%d or newer; this Python (%s) is %d.%d.%d, and %s.\n"
                         % (FLOOR + (sys.executable,) + tuple(sys.version_info[:3]) + (reason,)))
    raise SystemExit(0 if hook_event else 2)
