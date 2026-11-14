#!/usr/bin/env python3
"""Whether each Proof of a step plan can run at its step's done (step-plan round 2, the X-A measure; README.md).

A step's Proof runs when its implement reports done, before that step's test stage writes a test, and implement writes no
tests. Two forms of a Proof that needs a test not yet written:

- form 1 (a path): the Proof names a test-class path, in its words or inside inline code (`node -e`, `python3 -c`), that the
  item base lacks and no earlier step declares;
- form 2 (the focused suite): a whole shell segment of the Proof is a focused command of the plan that names no path and no
  inline code (`node --test`, `python3 -m unittest -v`), while no code or test file of the base holds any of its IDs.
  ``form2`` is that segment verbatim (the registered reading); ``form2_filtered`` (the amendment of README.md, made after arm B's
  pilot sample 4 and before any arm T sample) is a segment that also names no path or inline code and runs the same program
  as such a focused command (its first two words: `node --test`, `npm test`, `python3 -m`), with other options, such as
  `node --test --test-name-pattern='TC_2|TC_5'`. On a base with none of the IDs it finds only this item's tests, which do
  not exist yet at the step's done.

An item whose paths are all tests is exempt from both, as in rule A (`shiploop_item_scope.proof_order_refusal`). Knowledge files
are not searched for IDs: they record planned IDs (A-s9's environment.md lists TC_1-TC_5), not tests.
"""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_item_scope as scope  # noqa: E402

INLINE = frozenset(("-e", "-c", "--eval", "-p"))
OPERATORS = frozenset(("&&", "||", ";", "|", "&"))
SEARCHED = ("code", "test")


def words(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def segments(command: str) -> list[list[str]]:
    """The words of each shell segment of ``command`` (split on && || ; | &), quotes removed."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return [command.split()]
    found, current = [], []
    for token in tokens:
        if token in OPERATORS:
            found.append(current)
            current = []
        else:
            current.append(token)
    found.append(current)
    return [segment for segment in found if segment]


def named_paths(proof: str) -> list[str]:
    """The relative file paths a Proof names: ``scope.command_paths`` plus those inside its inline code.

    The inline reading is the shipped reader itself (``scope.inline_code_paths``). Until the second review this scorer
    held a copy of its patterns, kept equal by hand; each review fix then had to land twice.
    """
    return list(dict.fromkeys(list(scope.command_paths(proof)) + scope.inline_code_paths(proof)))


def holds_id(ident: str, texts: Mapping[str, str]) -> bool:
    pattern = re.compile(r"(?<![\w-])" + re.escape(ident) + r"(?![\w-])")
    return any(pattern.search(text) for path, text in texts.items() if scope.classify(path) in SEARCHED)


def classify(plan: Mapping[str, Any], base_files: Iterable[str], base_texts: Mapping[str, str]) -> dict:
    """{"form1": [{"step", "path"}], "form2": [{"step", "command"}], "form2_filtered": [{"step", "command", "segment"}]}
    for ``plan`` on a base holding ``base_files``. A segment that is a focused command verbatim is in ``form2`` only."""
    base = set(base_files)
    item_paths = [str(path) for path in plan.get("paths") or ()]
    if item_paths and all(scope.classify(path) == "test" for path in item_paths):
        return {"form1": [], "form2": [], "form2_filtered": []}
    focused = [row for row in plan.get("test_commands") or () if isinstance(row, Mapping) and row.get("suite") == "focused"]
    declared: set[str] = set()
    form1, form2, filtered = [], [], []
    for step in [row for row in plan.get("steps") or () if isinstance(row, Mapping)]:
        name, proof = str(step.get("id")), str(step.get("proof") or "")
        for path in named_paths(proof):
            if scope.classify(path) == "test" and path not in base and path not in declared:
                form1.append({"step": name, "path": path})
        parts = segments(proof)
        earlier_tests = any(scope.classify(path) == "test" for path in declared)
        for row in focused:
            command = str(row.get("command") or "")
            if not command or not scope.generic_command(command) or earlier_tests:
                continue
            if any(holds_id(str(ident), base_texts) for ident in row.get("ids") or ()):
                continue
            program = words(command)[:2]
            if words(command) in parts:
                form2.append({"step": name, "command": command})
                continue
            for part in parts:
                if len(program) == 2 and part[:2] == program and scope.generic_command(shlex.join(part)):
                    filtered.append({"step": name, "command": command, "segment": shlex.join(part)})
                    break
        declared.update(str(path) for path in step.get("paths") or ())
    return {"form1": form1, "form2": form2, "form2_filtered": filtered}
