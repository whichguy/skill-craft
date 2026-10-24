"""ShipLoop's glossary as data (run-5 batch, 2026-10-24): the retired terms its block lists, for the hermetic
retired-term test and the run record in metrics.json.

``skills/shiploop/references/glossary.md`` is the one place a ShipLoop term is defined. Its fenced block whose info
string is ``json retired-terms`` lists each retired term with the regular expression that finds it, the term that
replaced it, the date and the files allowed to name it (a refusal that tells a model it is retired). This module is
the one reader of that block.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GLOSSARY = ROOT / "skills" / "shiploop" / "references" / "glossary.md"
BLOCK = re.compile(r"^```json retired-terms\n(.*?)^```", re.M | re.S)
FIELDS = ("retired", "use", "since", "pattern", "allow")


def retired_terms(path: Path = GLOSSARY) -> list[dict[str, Any]]:
    """The glossary's retired terms, each with its ``pattern`` compiled as ``regex``.

    Raises ValueError, naming the problem, when the block is missing or a row is malformed."""
    found = BLOCK.search(path.read_text(encoding="utf-8"))
    if not found:
        raise ValueError(f"{path}: no ```json retired-terms block")
    rows = json.loads(found.group(1))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: the retired-terms block is a nonempty JSON list")
    terms = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError(f"{path}: retired term {index} needs exactly {', '.join(FIELDS)}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row["since"])) or not isinstance(row["allow"], list):
            raise ValueError(f"{path}: retired term {row['retired']!r} needs a YYYY-MM-DD since and an allow list")
        terms.append(dict(row, regex=re.compile(row["pattern"], re.M)))
    return terms


def digest(path: Path = GLOSSARY) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
