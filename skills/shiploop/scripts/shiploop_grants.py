"""ShipLoop's wording for the shared host write-grant probe (host_write_grants).

An isolated run writes beside the repository (``.shiploop-runs``: worktree,
run state) and into the repository's shared Git directory (``git worktree
add`` and every commit).  The probe, host detection and repair message live in
host_write_grants.py, vendored byte-identically with Ask Agent; this module
only names ShipLoop in the message.
"""
from __future__ import annotations

import os
from typing import Mapping

import host_write_grants
from host_write_grants import EXIT_GRANT_NEEDED, GrantError, detect_host, nearest_existing, require  # noqa: F401

MARKER = "SHIPLOOP-GRANT-NEEDED"
PRODUCT = host_write_grants.Product(
    marker=MARKER,
    outcome="ShipLoop did not start.",
    profile="shiploop",
    workarounds="editing the source checkout, running init in place, moving the workspace into the repository",
)


def report(error: GrantError, rerun: str, environ: Mapping[str, str] = os.environ) -> str:
    """The exact, host-first repair message printed on exit code 3."""
    return host_write_grants.report(error, rerun, PRODUCT, environ)
