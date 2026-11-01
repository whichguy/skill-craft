"""The Python floor of ShipLoop's scripts, checked before anything else is imported.

Every entry script imports this module first and calls ``require``.  Only syntax and calls that Python 3.7 accepts
belong here, so an older interpreter reaches the message instead of a ``TypeError`` from a later import (the library
modules subscript ``os.PathLike`` and call ``str.removeprefix``, both Python 3.9).
"""

import sys

FLOOR = (3, 9)


def require(hook_event=False):
    """Return on Python ``FLOOR`` or newer; otherwise exit 2 with one line, or exit 0 silently for a host hook event.

    A hook event runs on every tool call of every project, so on an interpreter below the floor it does nothing rather
    than print an error each time; the keepalive is simply absent.  The CLI states the requirement instead.
    """
    if sys.version_info >= FLOOR:
        return
    if not hook_event:
        sys.stderr.write("error: ShipLoop needs Python %d.%d or newer; this python3 is %d.%d.%d. "
                         "Put a newer python3 first on PATH.\n" % (FLOOR + tuple(sys.version_info[:3])))
    raise SystemExit(0 if hook_event else 2)
