"""Write a run's ShipLoop knowledge home, as a planning host would, for fixtures that pass a close."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/shiploop/scripts"))
import shiploop_knowledge as knowledge  # noqa: E402


def write(state: Mapping[str, Any]) -> None:
    """Create every file any close requires, when missing; spec.md carries one requirement ID."""
    repo = Path(str(state["repo"]))
    for names in knowledge.CLOSES.values():
        for name in names:
            path = repo / (name.replace("{feature}", knowledge.feature_dir(state)) if "{feature}" in name
                           else knowledge.HOME + "/" + name)
            if path.is_file():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            body = "R-1: Synthetic requirement.\n" if path.name == "spec.md" else "Synthetic knowledge.\n"
            if path.name == "outcome.md":
                body = "".join("## " + name + "\n\nSynthetic " + name.lower() + ".\n\n"
                               for name in knowledge.LEARNING_SECTIONS)
            path.write_text("# " + path.stem + "\n\n" + body, encoding="utf-8")
