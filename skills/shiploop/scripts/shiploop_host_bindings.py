"""Read ShipLoop's packaged host-bindings/v2 data for host detection and emit-time agent hints.

Kept byte-identical with ``skills/ask-agent/references/host-bindings.json`` (enforced by
``test/ask-agent-host.test.py``) so each skill package remains self-contained while sharing one
detection order, marker set, and measured binding schema. Python 3.9+ standard library only.
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

DATA = Path(__file__).resolve().parent.parent / "references" / "host-bindings.json"
SCHEMA = "skill-craft/host-bindings/v2"
KNOWN_HOSTS = ("codex", "grok", "opencode", "claude", "cursor", "antigravity", "unknown")


@functools.lru_cache(maxsize=4)
def _load_cached(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not a {SCHEMA} file")
    return data


def load(path: Path = DATA) -> dict[str, Any]:
    return _load_cached(str(path.resolve()))


def detect(environ: Mapping[str, str] = os.environ, data: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Detect the innermost host from exact non-empty marker env vars."""
    table = load() if data is None else data
    markers = table["detect"]["markers"]
    present = {host: sorted(name for name in names if environ.get(name)) for host, names in markers.items()}
    for host in table["detect"]["order"]:
        if present[host]:
            others = sorted(name for other, names in present.items() if other != host for name in names)
            return {"host": host, "detected_by": present[host], "also_present": others}
    return {"host": "unknown", "detected_by": [], "also_present": sorted(name for names in present.values() for name in names)}


def detect_host(environ: Mapping[str, str] = os.environ) -> str:
    """Return the detected host name (or ``unknown``)."""
    return str(detect(environ)["host"])


def binding_for(host: str, data: Optional[Mapping[str, Any]] = None) -> Optional[dict[str, Any]]:
    table = load() if data is None else data
    found = table["hosts"].get(host)
    return dict(found) if isinstance(found, Mapping) else None


def report(environ: Mapping[str, str] = os.environ, *, host_override: Optional[str] = None,
           data: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Compact host report matching ask_agent_host.py's structure."""
    table = load() if data is None else data
    if host_override and host_override != "auto":
        if host_override not in KNOWN_HOSTS:
            raise ValueError(f"unknown host override: {host_override!r}")
        found = {"host": host_override, "detected_by": ["override"], "also_present": []}
    else:
        found = detect(environ, table)
    binding = table["hosts"].get(found["host"])
    return {
        "schema": table["schema"],
        **found,
        "binding": binding,
        "authority": table["measured"]["authority"],
    }


def supports_fork(host: str, data: Optional[Mapping[str, Any]] = None) -> bool:
    binding = binding_for(host, data)
    return bool(binding and binding.get("fork_args") is not None)


def worker_capacity(host: str, default: int = 4, data: Optional[Mapping[str, Any]] = None) -> int:
    binding = binding_for(host, data)
    cap = binding.get("capacity") if binding else None
    if isinstance(cap, Mapping) and isinstance(cap.get("workers"), int) and cap["workers"] > 0:
        return int(cap["workers"])
    return default


def host_hint(environ: Mapping[str, str] = os.environ, *, host_override: Optional[str] = None,
              worktree: Optional[str] = None, data: Optional[Mapping[str, Any]] = None) -> str:
    """Emit-time 2-line host quirk hint (never persisted in state.md).

    Returns a short host-specific guardrail line when a known host is detected, or a neutral
    fallback when ``unknown``. The live native tool schema always takes precedence.
    """
    info = report(environ, host_override=host_override, data=data)
    host = info["host"]
    binding = info["binding"]
    if not binding:
        return ("Host hint (unknown): use your live native subagent tool schema; prefer blocking/foreground calls, "
                "never create a second worktree or cloud VM, and pass explicit working directories.")
    raw_hint = str(binding.get("hint") or "")
    if worktree:
        raw_hint = raw_hint.replace("<WORKTREE>", worktree)
    status = binding.get("status", "unqualified")
    tag = f"{host}, {status}" if status != "qualified" else host
    return f"Host hint ({tag}): {raw_hint} The live native tool schema wins where it differs."
