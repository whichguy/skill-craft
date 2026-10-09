"""Which hosts launched a run, read from the launch records its output folder keeps.

``invocation.json`` is the first launch; each later launch is ``invocation-resume-<host>-<seconds>.json``.  A regrade
starts no host but writes a resume record too (``versions.regraded``), so it is not a launch.  One reader, used by every
part of the harness that must know whether a run was one host's (the baseline cells, the environment record, the
resume defaults), so a run that two hosts worked on is named the same way everywhere.  sessionlog.py is the harness's
other per-launch record (sessions.jsonl: every host session with its start, end and the ledger at each); the two answer
different questions (which hosts launched, and where each session began and ended) and the older runs have only this one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

_RESUME = re.compile(r"^invocation-resume-(?P<host>[\w.-]+?)-(?P<stamp>\d+)\.json$")


def _read(path: Path) -> dict | None:
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def launches(out: Path) -> List[Tuple[str, dict]]:
    """``(file name, record)`` for every launch that started a host, first launch first."""
    out = Path(out)
    found: List[Tuple[int, str, dict]] = []
    first = _read(out / "invocation.json")
    if first is not None:
        found.append((0, "invocation.json", first))
    for path in out.glob("invocation-resume-*.json"):
        match = _RESUME.match(path.name)
        record = _read(path)
        if match is None or record is None or (record.get("versions") or {}).get("regraded"):
            continue
        found.append((int(match.group("stamp")), path.name, record))
    return [(name, record) for _stamp, name, record in sorted(found, key=lambda item: (item[0], item[1]))]


def launch_epochs(out: Path) -> List[int]:
    """The epoch second at which each launch after the first began, oldest first: the number in its record's name.

    The only record of where a later host session began in a run from before ``sessions.jsonl`` (see sessionlog.py, the
    harness's own per-session record, which says more and which a run since 2026-10-09 has). A regrade is not a launch.
    """
    return [int(_RESUME.match(name).group("stamp")) for name, _record in launches(out) if _RESUME.match(name)]


def unreadable(out: Path) -> List[str]:
    """Launch records that exist and cannot be read as a record (a file cut off mid-write, a directory, a list), by file name, the
    first launch's record first.  A run with one of these cannot say which hosts launched it: ``hosts_used`` and ``mixed_host`` skip
    the file, so a caller that must not read a shorter list as a complete one asks this too.  A file that is not there is not
    unreadable, and a name that is not a launch record's is not looked at."""
    out = Path(out)
    names: List[str] = []
    first = out / "invocation.json"
    if (first.exists() or first.is_symlink()) and _read(first) is None:
        names.append(first.name)
    for path in sorted(out.glob("invocation-resume-*.json")):
        if _RESUME.match(path.name) and _read(path) is None:
            names.append(path.name)
    return names


def hosts_used(out: Path) -> List[str]:
    """The distinct hosts that launched the run, in the order they first did."""
    hosts: List[str] = []
    for _name, record in launches(out):
        host = record.get("host")
        if isinstance(host, str) and host not in hosts:
            hosts.append(host)
    return hosts


def mixed_host(out: Path) -> bool:
    """True when more than one host worked on the run: its verdicts and costs belong to no one host."""
    return len(hosts_used(out)) > 1
