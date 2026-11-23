#!/usr/bin/env python3
"""Name this session's native host from its environment and print that host's measured binding.

    ask_agent_host.py

Prints one compact JSON line and exits 0. The host comes from exact environment variable names, innermost host first (a nested host
inherits its launcher's variables). A host with no binding is reported as ``unknown``, which is an answer, not an error. The binding
is data from references/host-bindings.json; the live native tool schema is authoritative and wins where they differ. The script launches
nothing, writes nothing and reads only the environment and that one file.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

DATA = Path(__file__).resolve().parent.parent / "references" / "host-bindings.json"
PROSE = "references/host-capabilities.md"
SCHEMA = "skill-craft/host-bindings/v2"


def load(path: Path = DATA) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not a {SCHEMA} file")
    return data


def detect(environ: Mapping[str, str], data: Mapping[str, Any]) -> dict[str, Any]:
    """The host named by the first marker group, in the data's order, that has any non-empty variable; the other groups' markers are reported."""
    markers = data["detect"]["markers"]
    present = {host: sorted(name for name in names if environ.get(name)) for host, names in markers.items()}
    for host in data["detect"]["order"]:
        if present[host]:
            others = sorted(name for other, names in present.items() if other != host for name in names)
            return {"host": host, "detected_by": present[host], "also_present": others}
    return {"host": "unknown", "detected_by": [], "also_present": sorted(name for names in present.values() for name in names)}


def report(environ: Mapping[str, str], data: Mapping[str, Any]) -> dict[str, Any]:
    found = detect(environ, data)
    binding = data["hosts"].get(found["host"])
    if binding:
        status = binding.get("status", "unqualified")
        if status == "unqualified":
            next_step = (f"Binding for {binding['name']} is unqualified: check the live native tool schema "
                         f"and follow {binding['section']}.")
        else:
            next_step = "Check the binding's tool names against the live native schema, then follow the named section of the host capabilities."
    else:
        next_step = f"No binding for this host: read {PROSE} and use the live native tool schema."
    return {"schema": data["schema"], **found, "binding": binding, "section": binding["section"] if binding else PROSE,
            "authority": data["measured"]["authority"], "next": next_step}


def main(argv: Sequence[str] | None = None) -> int:
    argparse.ArgumentParser(prog="ask_agent_host.py", description=__doc__.split("\n\n")[0]).parse_args(argv)
    try:
        value = report(os.environ, load())
    except (OSError, ValueError, KeyError) as exc:
        sys.stderr.write(json.dumps({"code": "bindings_unreadable", "observed": str(exc), "safe_next_step": f"Read {PROSE} and the live native schema."},
                                    sort_keys=True, separators=(",", ":")) + "\n")
        return 2
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
