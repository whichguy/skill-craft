"""Model-written fields that a packet prints as required text: whole within a print budget, or spilled to a run file.

ShipLoop accepts a field of any length (owner, 2026-10-28: plan F2/Q4 of
docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md).  Before, a gate refused a step's task, Proof or criteria, a
work item's context, its open assumptions or concern rows, a step's notes, the test layers and a headline once they
passed the size the later packets were measured at, and each refusal cost the model a rewrite (3-5 per run in the D7
before-runs).  A required block of a packet still prints such a field by value while it fits the block's print budget.
A longer one prints its leading lines that fit (the first cut to the budget when it alone passes it), then one line
naming the run file that holds it whole:

    RUN/fields/<action>-<field>.md

``<action>`` is the accepted action whose result holds the field, ``<field>`` names it inside that result (``S1-task``,
``W2-concerns``, ``test-layers``).  ``shiploop_navigator.emit`` writes each file, from state alone, before it prints the
packet that names it: a cleared context finds the file the packet names (S-6), and the printed text stays small (S-7).
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

DIR = "fields"


class Shown(NamedTuple):
    """What a packet prints for one field, and the run file to write when the field passed its budget."""

    lines: List[str]
    file: Optional[Tuple[str, str]]  # (run-relative path, the whole field) when the field was cut; None when whole


def path(action: str, field: str) -> str:
    """The run-relative file that holds ``field`` of ``action``'s result whole."""
    return DIR + "/" + action + "-" + field + ".md"


def cut(text: str, budget: int) -> str:
    """``text`` when it fits ``budget`` characters, else its first ``budget - 1`` and an ellipsis."""
    return text if len(text) <= budget else text[:budget - 1].rstrip() + "…"


def inline(text: str, budget: int, action: str, field: str) -> Shown:
    """A field printed on its label's line (a step's task or Proof): ``text`` as it is while it fits ``budget``; else its
    first line, cut to the budget, then the file that holds it.  The file keeps the field as written, so a spilled Proof
    runs as it is."""
    if len(text) <= budget:
        return Shown([text], None)
    relative = path(action, field)
    first = " ".join(text.strip().splitlines()[0].split())
    return Shown([cut(first, budget) + " (cut here: RUN/" + relative + " holds all " + f"{len(text):,}"
                  + " characters)"], (relative, text.strip("\n") + "\n"))


def block(lines: Sequence[str], size: int, budget: int, action: str, field: str, indent: str = "") -> Shown:
    """The lines of a required block (concern rows, criteria, test layers): all of them while ``size``, the field's own
    measure, fits ``budget``; else the leading lines that fit the budget, at least the first (cut to it), then a line
    naming the file that holds every line."""
    if size <= budget:
        return Shown(list(lines), None)
    relative = path(action, field)
    shown: List[str] = []
    used = 0
    for line in lines:
        if shown and used + len(line) + 1 > budget:
            break
        shown.append(line if shown else cut(line, budget))
        used += len(shown[-1]) + 1
    left = len(lines) - len(shown)
    told = (f"{left} more line{'s' if left != 1 else ''} not printed here" if left else "cut here")
    return Shown(shown + [indent + "(" + told + ": RUN/" + relative + " holds all " + str(len(lines)) + " whole)"],
                 (relative, "\n".join(lines) + "\n"))


__all__ = ("DIR", "Shown", "block", "cut", "inline", "path")
