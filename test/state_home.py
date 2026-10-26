"""Keep a suite's state out of the developer's ~/.local/state.

Until Loop's session stacks and ShipLoop's keepalive records live under
``$XDG_STATE_HOME`` (default ``~/.local/state``), keyed to the host session the
process runs in.  A suite run inside a Claude Code or Grok session inherits that
session's markers, so without this its records land in the developer's state
under the live session's key.  ``run_suites.run_process`` gives every suite a
private state home and fails one that leaves anything there; ``isolate`` gives a
suite the same protection when it runs on its own, as
``python3 -B test/<name>.test.py``.
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


# The stores' own overrides, which would send the suite's state to the developer's directories (as in run_suites).
STATE_OVERRIDES = ("UNTIL_LOOP_STATE_DIR", "SHIPLOOP_KEEPALIVE_HOME")


def isolate() -> Path:
    """Give this process, and every process it starts, a private XDG_STATE_HOME removed at exit.

    Call it once at module level, before anything copies ``os.environ``.  The
    path is resolved because macOS temporary paths sit under the /var symlink,
    which Until Loop refuses as a state root.
    """
    path = Path(tempfile.mkdtemp(prefix="skill-craft-suite-state-")).resolve()
    for key in STATE_OVERRIDES:
        os.environ.pop(key, None)
    os.environ["XDG_STATE_HOME"] = str(path)
    atexit.register(shutil.rmtree, path, True)
    return path
