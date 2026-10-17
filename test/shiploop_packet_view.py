"""Test support: a packet's top block found by constant and label, and its ORDER asserted, never an address.

A packet's first lines are its header, the owner rule, the pointer to the run's context index and the one legal
callback; the goal and the done-when follow (``shiploop_navigator._producer_blocks``).  Suites used to address those
lines by arithmetic (``lines[header + 1]``, ``lines[1 + OWNER]``), so a unit that inserted, moved or dropped one line of
the block failed a dozen assertions that checked nothing it had changed: 42.1 minutes from first red to commit for the
loop block and 24.6 for the reconcile, 64% of the edits pure re-pointing (test-economy review, 2026-10-17, pins P1-P3).

``assert_top_block`` finds each part by the constant that defines it (``prompts.OWNER_RULE``, the pointer's prefix and
suffix) or by the label its line starts with, and asserts that the parts that are there come in ``TOP_ORDER`` and sit
within ``TOP_WINDOW`` lines of the header.  A layout move edits ``TOP_ORDER`` or a label here, once, not every suite.

A part that is required and not found FAILS: a lookup that finds nothing must never pass.  The negative self-test in
``test/shiploop-packet-recut.test.py`` (``TopBlockHelperTests``) keeps that true.

The same module reads which outcomes a packet or a refusal tells the model to report (``named_outcomes``) so a test can
check them against ``STAGE_SPEC[stage].outcomes`` (memory test-the-route-not-the-wording).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Union

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

HEADER_PREFIX = "ShipLoop navigator | "

# The labels a packet's one legal callback line starts with (``shiploop_navigator._first_callback_lines``; a started
# Improve child's packet is two numbered instructions and the second is its callback; an unbound child's first line is
# the improve-bind command, with or without the sentence about the missing card).
CALLBACK_LABELS = ("Callback for this stage", "2. When the improve skill has completed, run:", "Next command (",
                   "No Improve card is recorded for this run.")

# The parts of the top block in the order a packet prints them.  This tuple is the one place that says so: when a unit
# moves a part, it edits the tuple (and the part's finder below), not the suites that call ``assert_top_block``.
TOP_ORDER = ("header", "owner", "pointer", "callback", "goal", "done_when")

# Every part sits this many lines after the header or nearer: plan 6.1, "the first 14 lines after the header hold both
# pointer lines, the callback and Goal".  Not an address: a part may move inside the window and nothing fails.
TOP_WINDOW = 14

# What each default requires.  A packet that is not a producer's (paused, halted, done, the bound Improve packet) has no
# callback or goal; a caller names the parts it requires.
DEFAULT_REQUIRE = ("owner", "pointer", "callback")


def _finders(callback_labels: Sequence[str]) -> dict[str, Callable[[str], bool]]:
    return {
        "header": lambda line: line.startswith(HEADER_PREFIX),
        "owner": lambda line: line == prompts.OWNER_RULE,
        "pointer": lambda line: (line.startswith(prompts.INDEX_POINTER_PREFIX)
                                 and line.endswith(prompts.INDEX_POINTER_SUFFIX)),
        "callback": lambda line: line.startswith(tuple(callback_labels)),
        "goal": lambda line: line.startswith("Goal: "),
        "done_when": lambda line: line.startswith("Done when"),
    }


class TopBlock:
    """The parts of a packet's top block that were found: ``lines`` is the packet, ``at`` maps a part to its line index.

    A caller reads a part's text with ``view["callback"]`` and asks for the position of a line it names itself with
    ``find``; it never computes an address from the header.
    """

    def __init__(self, lines: list[str], at: dict[str, int]) -> None:
        self.lines = lines
        self.at = at

    def __contains__(self, part: str) -> bool:
        return part in self.at

    def __getitem__(self, part: str) -> str:
        """The text of a part that was found (KeyError names the part when it was not)."""
        return self.lines[self.at[part]]

    def index(self, part: str) -> int:
        return self.at[part]

    def find(self, prefix: str, *, after: str = "header") -> tuple[int, str]:
        """The first line after the part ``after`` that starts with ``prefix``: ``(index, line)``.  Raises AssertionError
        when there is none, so a lookup that finds nothing cannot pass."""
        start = self.at[after] + 1 if after in self.at else 0
        for number in range(start, len(self.lines)):
            if self.lines[number].startswith(prefix):
                return number, self.lines[number]
        raise AssertionError(f"no line after the {after} starts with {prefix!r}")

    def text_after(self, number: int) -> str:
        """The line after line ``number``: for a pair that is adjacent by meaning (a command and its argument line), where
        ``number`` came from ``find`` and is not an address computed from the header."""
        return self.lines[number + 1]


def top_block(text: Union[str, Sequence[str]], *, callback_labels: Sequence[str] = CALLBACK_LABELS) -> TopBlock:
    """Find the parts of a packet's top block.  Asserts nothing; a part that is not there is not in ``at``.

    The header is the first line that starts with ``HEADER_PREFIX`` (an inline prefix may precede it); each other part is
    the first line after the header that the part's finder accepts.
    """
    lines = text.splitlines() if isinstance(text, str) else list(text)
    at: dict[str, int] = {}
    finders = _finders(callback_labels)
    header = next((number for number, line in enumerate(lines) if finders["header"](line)), None)
    if header is not None:
        at["header"] = header
        for part in TOP_ORDER[1:]:
            number = next((n for n in range(header + 1, len(lines)) if finders[part](lines[n])), None)
            if number is not None:
                at[part] = number
    return TopBlock(lines, at)


def assert_top_block(test: unittest.TestCase, text: Union[str, Sequence[str]], *,
                     require: Iterable[str] = DEFAULT_REQUIRE, callback_labels: Sequence[str] = CALLBACK_LABELS,
                     within: Optional[int] = TOP_WINDOW, label: str = "") -> TopBlock:
    """Assert a packet's top block: the header, every part in ``require`` is found, the parts found come in
    ``TOP_ORDER`` and each lies within ``within`` lines of the header.  Returns the view for further assertions.

    ``require`` names the parts the caller expects ("owner", "pointer", "callback", "goal", "done_when"); the header is
    always required.  A part not required is still ordered and bounded when the packet has it.  ``within=None`` skips
    the bound.  ``label`` names the packet in a failure (a stage, a route).
    """
    view = top_block(text, callback_labels=callback_labels)
    where = (label + ": ") if label else ""
    if "header" not in view:
        test.fail(where + f"no line starts with {HEADER_PREFIX!r}")
    for part in require:
        if part not in TOP_ORDER:
            test.fail(where + f"{part!r} is not a part of the top block {TOP_ORDER}")
        if part not in view:
            test.fail(where + f"the packet has no {part} line after its header (looked for {_describe(part, callback_labels)})")
    previous = "header"
    for part in TOP_ORDER[1:]:
        if part not in view:
            continue
        if view.index(part) <= view.index(previous):
            test.fail(where + f"the {part} line (line {view.index(part)}) must come after the {previous} line "
                      f"(line {view.index(previous)}); the order is {' < '.join(TOP_ORDER)}")
        previous = part
    if within is not None:
        for part in TOP_ORDER[1:]:
            if part in view and view.index(part) - view.index("header") > within:
                test.fail(where + f"the {part} line is {view.index(part) - view.index('header')} lines after the header, "
                          f"not within {within}")
    return view


def _describe(part: str, callback_labels: Sequence[str]) -> str:
    return {"owner": "prompts.OWNER_RULE",
            "pointer": "a line from prompts.INDEX_POINTER_PREFIX to INDEX_POINTER_SUFFIX",
            "callback": " or ".join(repr(label) for label in callback_labels),
            "goal": "'Goal: '", "done_when": "'Done when'"}[part]


# ------------------------------------------------------------------ the callback command and the result path it names

def callback_line(text: Union[str, Sequence[str]]) -> str:
    """The packet's producer callback line (the label ``Callback for this stage``).  Raises AssertionError when there is
    none, so a lookup that finds nothing cannot pass."""
    lines = text.splitlines() if isinstance(text, str) else list(text)
    for line in lines:
        if line.startswith("Callback for this stage"):
            return line
    raise AssertionError("the packet has no 'Callback for this stage' line")


def callback_argv(text: Union[str, Sequence[str]]) -> list[str]:
    """The argv of the callback command: the text after the label's closing ``): `` up to the end of the line.  The label
    may change (it names the result path and, later, the way to run the command); the command starts at ``python3``."""
    import shlex
    line = callback_line(text)
    return shlex.split(line[line.index("): python3 ") + 3:])


def callback_result_path(text: Union[str, Sequence[str]]) -> Path:
    """The absolute result path the callback's label names (``<run>/inbox/<action>.md``).  The command has no ``--result``
    flag (``complete`` reads that one path by default), so the label is where a packet says where to write the result."""
    line = callback_line(text)
    label = line[:line.index("): python3 ")]
    found = re.search(r"written to (/.*?/inbox/[^/\s)]+\.md)", label)   # a run directory may hold spaces
    if found is None:
        raise AssertionError("the callback label names no inbox result path: " + label)
    return Path(found.group(1))


# ------------------------------------------------------------------ the outcomes a packet or a refusal names

# The outcome words of the whole graph, read from the stage table, never listed here.
OUTCOME_WORDS = frozenset(outcome for row in stage_spec.STAGE_SPEC.values() for outcome in row.outcomes)
# Only these two phrases name an outcome to report ("report revise ...", "Report outcome replan now ..."): a wider reading
# would match "report it", "reported" and prose that is not an instruction.
_NAMED_OUTCOME = re.compile(r"\b[Rr]eport (?:outcome )?(" + "|".join(sorted(OUTCOME_WORDS)) + r")\b")


def named_outcomes(text: str) -> list[str]:
    """The outcomes ``text`` tells the model to report, in order of appearance, each once."""
    found: list[str] = []
    for match in _NAMED_OUTCOME.finditer(text):
        if match.group(1) not in found:
            found.append(match.group(1))
    return found


def unaccepted_outcomes(stage: str, text: str) -> list[str]:
    """The outcomes ``text`` tells the model to report that ``stage`` does not accept: the route a gate refuses (the A1
    class).  Empty when every one is in ``STAGE_SPEC[stage].outcomes``."""
    accepted = stage_spec.STAGE_SPEC[stage].outcomes
    return [outcome for outcome in named_outcomes(text) if outcome not in accepted]
