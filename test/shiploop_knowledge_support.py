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
    repo = Path(str(state["repo"]))
    for names in knowledge.CLOSES.values():
        for name in names:
            path = repo / knowledge.HOME / name
            if path.is_file():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            body = sections(name) if name in knowledge.SECTIONS else "Synthetic knowledge.\n"
            path.write_text("# " + path.stem + "\n\n" + body, encoding="utf-8")


def write_spec(state: Mapping[str, Any]) -> None:
    """Create spec.md with its sections and R-1, when missing: what a spec stage writes before its done, whose
    ``primary`` must name an R-<n> with an entry there (run-5 batch F6)."""
    path = Path(str(state["repo"])) / knowledge.HOME / "spec.md"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# spec\n\n" + sections("spec.md"), encoding="utf-8")
