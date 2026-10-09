"""Which hosts launched a run, read from the launch records its output folder keeps.

``invocation.json`` is the first launch; each later launch is ``invocation-resume-<host>-<seconds>.json``.  A regrade
starts no host but writes a resume record too (``versions.regraded``), so it is not a launch.  One reader, used by every
part of the harness that must know whether a run was one host's (the baseline cells, the environment record, the
resume defaults), so a run that two hosts worked on is named the same way everywhere.
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
