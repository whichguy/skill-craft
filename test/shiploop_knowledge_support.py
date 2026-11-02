"""Write a run's ShipLoop knowledge home, as a planning host would, for fixtures that pass a close."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/shiploop/scripts"))
import shiploop_knowledge_home as knowledge  # noqa: E402


def sections(name: str) -> str:
    """The body of a living file with every one of its ``knowledge.SECTIONS``, each with text; spec.md carries one requirement ID.

    A fixture whose home has all of its sections gets no section notice at its closes (a home with none prints a line per
    section on the CLI's stdout at each close, which a test of anything else would have to step around).
    """
    return "".join("## " + heading + "\n\n" + ("R-1: Synthetic requirement.\n" if (name, heading) == ("spec.md", "Requirements")
                                                else "Synthetic knowledge.\n") + "\n" for heading in knowledge.SECTIONS[name])


def write(state: Mapping[str, Any]) -> None:
    """Create every file any close requires, when missing; spec.md carries one requirement ID.

    A living file with named sections (``knowledge.SECTIONS``) is written with all of them.
    """
    for names in knowledge.CLOSES.values():
        for name in names:
            path = knowledge.artifact_path(state, name)
            if path.is_file() and (name != "spec.md" or path.stat().st_size > 0):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            body = sections(name) if name in knowledge.SECTIONS else "Synthetic knowledge.\n"
            # A fresh run's candidate exists but starts empty; fixture setup may
            # fill that placeholder. This helper never runs in production.
            path.write_text("# " + path.stem + "\n\n" + body, encoding="utf-8")


def write_spec(state: Mapping[str, Any]) -> None:
    """Create or fixture-fill the selected spec with sections and R-1 for the primary gate.

    Pure fixtures write the aggregate that would be copied at first save. Bound
    fixtures write the already-initialized run candidate; they never reseed it.
    """
    path = knowledge.artifact_path(state, "spec.md")
    if not path.is_file() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# spec\n\n" + sections("spec.md"), encoding="utf-8")
