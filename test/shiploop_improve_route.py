"""The Improve skill's ShipLoop route file, for the tests that pin handoff text which moved there (efficiency plan U18).

The text that was the same in every Improve handoff (ownership, recovery, the stopped-child route, exclusions, the
``final_result`` rules, the fixed review inputs) is in skills/improve/references/shiploop-route.md, word for word; a test that
pins one of those sentences looks in the handoff and the route together, so a sentence cannot vanish from both.
"""
from pathlib import Path

ROUTE = Path(__file__).resolve().parents[1] / "skills" / "improve" / "references" / "shiploop-route.md"


def route_text() -> str:
    return ROUTE.read_text(encoding="utf-8")


def with_route(text: str) -> str:
    """``text`` followed by the route file."""
    return text + "\n" + route_text()
