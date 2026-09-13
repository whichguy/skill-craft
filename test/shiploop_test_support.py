"""Small shared test-only helpers for ShipLoop packet assertions."""

from __future__ import annotations

import sys
from typing import TextIO


def report_advisory_size(
    label: str, text: str, guideline: int, *, stream: TextIO | None = None
) -> int:
    """Measure rendered prose without turning the guideline into a test gate."""
    size = len(text)
    relation = "within" if size <= guideline else "over"
    print(
        f"[shiploop size advisory] {label}: {size} characters "
        f"({relation} {guideline}-character guideline)",
        file=sys.stderr if stream is None else stream,
    )
    return size
