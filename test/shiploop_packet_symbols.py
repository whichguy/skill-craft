"""Test support: write a packet's References symbols back as the absolute paths they stand for.

A packet defines HOME, RUN, WORKTREE and GUIDES once (its References block) and names files by those symbols in prose
(owner, 2026-10-16).  A test that pins WHICH file a packet routes to, such as a guide locator, reads the packet through
``guides_expanded`` and keeps asserting the absolute path; a test about the symbols themselves reads the packet as printed.
"""
from __future__ import annotations

import re

# The text after each symbol's path in the definition lines (shiploop_navigator._reference_global_lines).
_DEFINITIONS = {
    "HOME": r"HOME = (.+?) \(knowledge home\)",
    "RUN": r"RUN = (.+?) \(run records\)",
    "GUIDES": r"GUIDES = (.+?) \(the skill's guides\)",
    "WORKTREE": r"(?m)^WORKTREE = (.+?) \(all product work",
}


def definitions(packet: str) -> dict[str, str]:
    """{symbol: absolute path} from the packet's References block; empty when it has none."""
    found = {}
    for name, pattern in _DEFINITIONS.items():
        match = re.search(pattern, packet)
        if match:
            found[name] = match.group(1)
    return found


def expanded(packet: str, symbols: tuple[str, ...] = ("HOME", "RUN", "GUIDES")) -> str:
    """``packet`` with each of ``symbols`` followed by a path written as its absolute path (definition lines untouched)."""
    paths = definitions(packet)
    out = []
    for line in packet.split("\n"):
        if not re.match(r"(?:HOME|WORKTREE) = ", line):
            for name in symbols:
                if name in paths:
                    line = re.sub(r"\b" + name + r"/(?=[\w.@+~-])", lambda _m, p=paths[name]: p + "/", line)
        out.append(line)
    return "\n".join(out)


def guides_expanded(packet: str) -> str:
    """``packet`` with GUIDES/<file> written as the absolute path of the guide."""
    return expanded(packet, ("GUIDES",))
