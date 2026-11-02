"""The route a run began with, read from what its start left on disk, and a watcher that ends the host once a run has started.

`workspace start` (the isolated entry) writes a workspace.md beside the run it makes; `init` (the direct entry) writes only
the run's state.md. Reading the folder needs no pattern for the many ways a model can write a command (a shell line, a
variable, a Python argument list with escaped quotes), and a refused `init`, which writes nothing, reads as no start. The route
is recorded as `start_route` in result.json and in the baseline row. With `--stop-after-start` the watcher ends the host at the
first start, so a question about a run's first command costs seconds, not a run (docs/experiments/start-route-20261101).
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

POLL_SECONDS = 1.0
WORKSPACE = "workspace.md"
SKIPPED = ("home", "build")  # the throwaway home and the plugin build are large and hold no run of the host's


def _search(out: Path, name: str) -> Iterator[Path]:
    """Files called ``name`` anywhere under ``out`` except home/ and build/."""
    try:
        entries = sorted(out.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.name in SKIPPED:
            continue
        try:
            if entry.is_dir():
                yield from entry.rglob(name)
            elif entry.name == name:
                yield entry
        except OSError:
            continue


def route(out) -> str | None:
    """``workspace`` once the isolated entry has made a workspace, ``direct`` once a run exists without one, None before
    ShipLoop has started a run under ``out``."""
    out = Path(out)
    for record in _search(out, WORKSPACE):
        root = record.parent
        # workspace.md is written before the internal init (and a blocked one is written when the source changed), so only a
        # run state inside the workspace shows that the isolated entry started a run.
        if (root / "run" / "state.md").is_file():
            return "workspace"
    import run_choice  # the harness's own definition of a ShipLoop run: a state.md that reads as a run's state

    return "direct" if run_choice.shiploop_runs(out) else None


def recorded(watch, out) -> str | None:
    """The route to record for a run: the first one the watcher saw while the run was starting, else what the folder reads now.
    The folder at the end can hold a direct run and a workspace made later, and ``route`` ranks the workspace first."""
    return (watch.route if watch is not None else None) or route(out)


class StartWatcher:
    """Creates ``stop_file`` as soon as the host's ShipLoop run has started, so the session ends on the harness's own stop path
    (status "stopped": the resume loop does not relaunch it and the run's records are still written). A daemon thread."""

    def __init__(self, out, stop_file, poll: float = POLL_SECONDS):
        self.out, self.stop_file, self.poll = Path(out), Path(stop_file), poll
        self.route: str | None = None
        self.ended = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def start(self) -> StartWatcher:
        self.thread.start()
        return self

    def stop(self) -> None:
        self.ended.set()
        if self.thread.is_alive():
            self.thread.join(timeout=10)

    def _watch(self) -> None:
        while not self.ended.wait(self.poll):
            try:
                found = route(self.out)
            except Exception:  # noqa: BLE001 - fail-open: a read problem never ends a session
                found = None
            if found:
                self.route = found
                self.stop_file.touch()
                return
