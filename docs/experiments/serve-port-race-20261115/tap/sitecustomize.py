"""A tap on serve.py: with this folder first on PYTHONPATH and SERVE_TAP_FILE set, every run of checks/serve.py appends one JSON line
to that file when it ends: when it started, how long it ran, and what it printed (its FAIL line, or the check's failure line, or nothing).
Nothing else is changed: the suite under test runs unmodified and does not know. Used to count how many times a suite starts a candidate
through serve.py and how those runs ended. Only a process whose script is serve.py is tapped."""

import atexit
import json
import os
import sys
import time

if sys.argv and os.path.basename(sys.argv[0]) == "serve.py" and os.environ.get("SERVE_TAP_FILE"):
    _began, _kept = time.time(), []

    class _Tee:
        def __init__(self, inner):
            self._inner = inner

        def write(self, text):
            if sum(map(len, _kept)) < 1500:
                _kept.append(text)
            return self._inner.write(text)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    sys.stdout = _Tee(sys.stdout)

    def _log() -> None:
        row = {"t": round(_began, 3), "seconds": round(time.time() - _began, 3), "pid": os.getpid(), "printed": "".join(_kept)[:1500],
               "pinned": os.environ.get("E2E_SERVE_PORT") or None}
        with open(os.environ["SERVE_TAP_FILE"], "a") as out:
            out.write(json.dumps(row) + "\n")

    atexit.register(_log)
