"""A brownfield case's base (SPEC "The promotion contract", build step 6; R10 of the final verdict): the existing project a
case starts from, instead of an empty folder.

A case opts in with ``base`` in cases.json: ``{"fixture": <folder under fixtures/>, "digest": <12 hex>, "source": why}``.
The digest is ``boundary.files_digest`` over the fixture's files, so it sits in the case's catalog entry and ``boundary.case``
changes whenever the base does.

* ``resolve`` is the case's base folder after checking its pin; a missing fixture or a stale pin is refused (SystemExit)
  before anything starts.
* ``start`` copies the base into an empty ``work/`` and commits it, and returns the run's ``base`` record (fixture, digest,
  the commit it starts from, the files committed). Run before the host, so the model's first sight is the base, committed.

Reads the fixture only; ``start`` writes only into the ``work/`` it is given.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402  (boundary.files_digest: the one digest of a set of files)

FIXTURES = HERE / "fixtures"
SKIPPED = ("node_modules", "__pycache__")  # never part of a base: installed or compiled, not written
IDENTITY = ["-c", "user.name=ShipLoop E2E base", "-c", "user.email=shiploop-e2e-base@example.invalid"]


def base_files(folder: Path) -> list[Path]:
    """Every file of a base folder, without installed or compiled ones."""
    found = []
    for here, folders, names in os.walk(folder):
        folders[:] = [name for name in folders if name not in SKIPPED]
        found += [Path(here) / name for name in names if not name.endswith(".pyc")]
    return sorted(found)


def digest(folder: Path) -> str | None:
    """The base's pin: 12 hex over its files' paths and bytes, or None when one cannot be read."""
    return boundary.files_digest(folder, base_files(folder))[0]


def resolve(case: dict | None) -> Path | None:
    """The case's base folder, its pin checked; None for a case without a base."""
    spec = (case or {}).get("base")
    if not spec:
        return None
    folder = FIXTURES / spec["fixture"]
    if not folder.is_dir():
        raise SystemExit(f"base: the case's fixture {spec['fixture']!r} is not a folder under {FIXTURES}")
    found = digest(folder)
    if found != spec.get("digest"):
        raise SystemExit(f"base: fixtures/{spec['fixture']} digests to {found}, not the {spec.get('digest')} the case pins; "
                         "a base change is a case change: update the pin in cases.json with it")
    return folder


def start(work: Path, case: dict | None) -> dict | None:
    """Copy the case's base into the empty `work` and commit it; the run's ``base`` record, or None for a case without one."""
    folder = resolve(case)
    if folder is None:
        return None
    for source in base_files(folder):
        target = work / source.relative_to(folder)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # The commit must not depend on the machine's Git config, as the seed's does not (run.seed_run).
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    for args in (["init", "-q"], ["add", "-A"], [*IDENTITY, "commit", "-qm", f"base: {case['base']['fixture']}"]):
        subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True, env=env)
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
                          env=env).stdout.strip()
    return {"fixture": case["base"]["fixture"], "digest": case["base"]["digest"], "start_head": head,
            "files": len(base_files(folder))}
