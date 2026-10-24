"""The Improve skill's ShipLoop route files, for the tests that pin handoff text which moved there (efficiency plan U18).

The text that was the same in every Improve handoff (ownership, recovery, the stopped-child route, exclusions, the
``final_result`` rules, the fixed review inputs) is in the ShipLoop route, word for word: since 2026-10-24 that is a short
core (skills/improve/references/shiploop-route.md, what every child reads) and the case files it names, opened only when
their case arises. A test that pins one of those sentences looks in the handoff and the whole route together, so a sentence
cannot vanish from all of them.
"""
from pathlib import Path

REFERENCES = Path(__file__).resolve().parents[1] / "skills" / "improve" / "references"
ROUTE = REFERENCES / "shiploop-route.md"
# The core first, then each file it names with the case that opens it.
CASE_FILES = tuple(REFERENCES / name for name in (
    "shiploop-route-rules.md",        # the long form of the core's every-pass rules
    "shiploop-route-recovery.md",     # errors, lost state, interrupted passes, the inline route text, the stopped child
    "shiploop-route-ask-agent.md",    # Route: ask-agent
    "shiploop-route-cases.md",        # independent review, later decisions, external operations, verify_script, final_result
    "shiploop-review-inputs.md",      # the fixed review inputs, one section per condition
))
ROUTE_FILES = (ROUTE, *CASE_FILES)


def route_text() -> str:
    """The whole ShipLoop route: the core and every case file, in that order."""
    return "\n".join(path.read_text(encoding="utf-8") for path in ROUTE_FILES)


def with_route(text: str) -> str:
    """``text`` followed by the whole route."""
    return text + "\n" + route_text()
