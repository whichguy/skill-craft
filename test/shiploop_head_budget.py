"""Test support: a printed packet's length at a reference install, and the journaled ceiling of each stage's head.

Grok gives the model an output whole up to 20,000 characters and, above that, only its first and last ~10,000 with the middle
elided (measured 2026-10-17, docs/experiments/shiploop-eff-evidence-20261017/plan/ADDENDUM-cut.md), and what is elided is
never read. What a packet prints depends on where the run and the skill live: the run directory appears a dozen times in a
head and the skill's path a few times, so the same text is 600 characters longer under a deep checkout than under a plugin
cache, and a head over ``PRINT_LIMIT`` also drops its quoted knowledge, so its shape depends on those lengths too. A ceiling
in a test must not move with the machine that runs it, so a test builds its packets inside ``reference_tmpdir`` (the run
directory is exactly ``REFERENCE_RUN_DIR_LENGTH`` characters when the system temp directory allows it) and compares
``at_reference_install``, which rewrites what remains (the skill's path to ``REFERENCE_ROOT_LENGTH`` characters, the bare
``shiploop`` the offline walk prints to the ``REFERENCE_CLI_LENGTH``-character CLI path of a plugin-cache install).

``test/shiploop_e2e/head_table.json`` holds, for every producer stage and route, the journaled value of the stage's printed head
and of its whole text (a packet whose whole text fits ``PRINT_LIMIT`` prints whole, and which of the two a stage prints
depends on the path lengths of the machine, near the limit).  A printed text above its value fails its test; a change that
grows a packet says so by raising the value in the same commit, with the reason in the journal.  ``over_the_cut`` lists the
heads above ``HOST_CUT`` today (a recorded gap that the print-order unit closes, not a goal); a head that newly crosses the cut
fails even when its value is raised.
"""
from __future__ import annotations

import contextlib
import json
import re
import secrets
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = json.loads((ROOT / "test/shiploop_e2e/head_table.json").read_text(encoding="utf-8"))

HOST_CUT = 20_000
REFERENCE_RUN_DIR_LENGTH = TABLE["reference"]["run_dir_length"]    # the run directory: <tmp>/shiploop-step-packets-xxxxxxxx/run
REFERENCE_ROOT_LENGTH = TABLE["reference"]["root_length"]          # the skill's package root in a plugin cache
REFERENCE_CLI_LENGTH = TABLE["reference"]["cli_path_length"]       # <root>/skills/shiploop/scripts/shiploop
BARE_CLI = "python3 shiploop "
OFFLINE_SUFFIX = "/shiploop-step-packets-xxxxxxxx/run"   # what the offline walk adds to the temp directory to name the run

_WORKTREE = re.compile(r"(?m)^WORKTREE = (\S+) \(all product work")


def reference_measure(workdir: str, root: Path | str = ROOT, run_dir_length: int = REFERENCE_RUN_DIR_LENGTH):
    """The length function a head's budget decisions use in a test: a text's length as if the run directory, the skill's
    root and the CLI path had their reference lengths (``at_reference_install`` for any part of a packet, not only a whole).

    ``workdir`` is the offline walk's work directory (the run directory is ``<workdir>/run``).  Without it a head would
    keep the lookups that fit under *this machine's* paths, and its length at the reference install would move with the
    checkout it is measured in.
    """
    workdir_length = run_dir_length - len("/run")
    root = str(root)

    def measure(text: str) -> int:
        return (len(text)
                + text.count(workdir) * (workdir_length - len(workdir))
                + text.count(root) * (REFERENCE_ROOT_LENGTH - len(root))
                + text.count(BARE_CLI) * (REFERENCE_CLI_LENGTH - len("shiploop")))
    return measure


def at_reference_install(text: str, root: Path | str = ROOT, run_dir_length: int = REFERENCE_RUN_DIR_LENGTH) -> int:
    """``len(text)`` as if the run directory, the skill's root and the CLI path had their reference lengths.

    The run directory is ``<workdir>/run`` and the packet's WORKTREE is ``<workdir>`` (both offline walks and ``emit`` in a
    temporary directory), so the work directory's length is read from the References block.  Every occurrence of the three
    paths is rewritten by the difference in length, as a real install would print them.
    """
    found = _WORKTREE.search(text)
    if found is None:
        raise AssertionError("the packet defines no WORKTREE: it has no References block to read the work directory from")
    return reference_measure(found.group(1), root, run_dir_length)(text)


def mode_of(whole: str, print_limit: int) -> str:
    """What ``emit`` prints for a packet whose full text is ``whole``: all of it (``whole``) when it fits ``print_limit``,
    otherwise its ``head`` (the rest is in the packet file)."""
    return "whole" if len(whole) <= print_limit else "head"


@contextlib.contextmanager
def reference_tmpdir(run_dir_length: int = REFERENCE_RUN_DIR_LENGTH):
    """Make the temp directory such that an offline run's directory (``<tmp>/shiploop-step-packets-xxxxxxxx/run``) has
    ``run_dir_length`` characters, by nesting under the system temp directory.  A system temp directory already that long
    (macOS: 48 characters, reference 83) or longer is left as it is; ``at_reference_install`` still corrects the length."""
    base_length = run_dir_length - len(OFFLINE_SUFFIX)
    system, before, made = tempfile.gettempdir(), tempfile.tempdir, None
    try:
        pad = base_length - len(system) - 1
        if pad >= 1:
            made = Path(system) / secrets.token_hex(pad)[:pad]
            made.mkdir()
            tempfile.tempdir = str(made)
        yield
    finally:
        tempfile.tempdir = before
        if made is not None:
            shutil.rmtree(made, ignore_errors=True)


def ceiling(route: str, stage: str, mode: str) -> int:
    """The journaled value of ``stage`` on ``route`` (``inline`` or ``ask-agent``) printed as a ``head`` or ``whole``."""
    return TABLE["heads"][route][stage][mode]


def known_over_the_cut(route: str) -> list:
    """The stages whose head is recorded as above ``HOST_CUT`` on ``route`` (a list the table names, not derived from values)."""
    return list(TABLE["over_the_cut"][route])
