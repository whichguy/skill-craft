"""Finish the current inner stage's Until Loop through the real runtime, for tests that drive ShipLoop's CLI.

Every inner stage's ``complete`` checks the loop's receipt against the contract ShipLoop rebuilds from the run state
(owner decision 2026-10-10).  Tests therefore run the loop the way a model does: the bundled until-loop runtime starts
from ShipLoop's own contract file and takes one report per iteration.  Nothing here writes a receipt by hand, so a
fixture cannot pass a receipt the runtime would not produce.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_loops as loops  # noqa: E402
import shiploop_store as store  # noqa: E402

_REPORTS = {
    "done": ("trivial", "satisfied", "allowed"),
    "blocked": ("non-trivial", "unsatisfied", "blocked"),
}


def _report(kind: str, note: str) -> str:
    classification, exit_assessment, continuation = _REPORTS[kind]
    return json.dumps({"classification": classification, "exit_assessment": exit_assessment,
                       "continuation_assessment": continuation,
                       "evidence": "Test fixture iteration: " + note,
                       "handoff": "Test fixture: no product facts to carry; " + note})


def _run(argv: list[str], stdin: str) -> dict[str, Any]:
    done = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=60, check=False)
    if done.returncode not in (0, 1):
        raise RuntimeError("until-loop runtime failed: " + done.stderr + done.stdout)
    return json.loads(done.stdout)


def finish_loop(run_dir: Path, *, outcome: str = "done", note: str = "fixture") -> Path:
    """Run the current inner action's loop to its end; return the receipt path.

    ``outcome`` "done" ends the loop satisfied; "blocked" stops it blocked.  An existing terminal receipt is reused.
    """
    run_dir = Path(run_dir)
    state = store.read_record(run_dir / "state.md")
    cursor = loops.cursor(state)
    if cursor is None:
        raise RuntimeError("no current inner action to run a loop for")
    action_id = cursor[1]
    contract_file = run_dir / loops.contract_path(action_id)
    if not contract_file.is_file():
        for relative, text in loops.contract_writes(run_dir, state).items():
            target = run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    receipt = loops.receipt_path(run_dir, action_id)
    if receipt.is_file():
        packet = json.loads(receipt.read_text(encoding="utf-8"))
        if packet.get("status") != "active":
            return receipt
    else:
        bound = loops.runtime(state)
        packet = _run([sys.executable, bound["runtime_cli"], "start", "--receipt", str(receipt)],
                      contract_file.read_text(encoding="utf-8"))
    for _ in range(10):
        if packet.get("status") != "active":
            return receipt
        packet = _run(list(packet["done_argv"]), _report(outcome, note))
    raise RuntimeError("the fixture loop did not end within 10 iterations")


def with_receipt(result: Mapping[str, Any], receipt: Path) -> dict[str, Any]:
    """``result`` with the receipt in evidence_refs, as the printed template prefills it."""
    refs = [str(ref) for ref in result.get("evidence_refs", []) if str(ref) != str(receipt)]
    return {**result, "evidence_refs": [str(receipt), *refs]}


# The labels that open the five fields of the Until Loop argument, in order (shiploop_loops.invoke_lines).
ARGUMENT_FIELDS = ("Work: ", "Exit when ALL of these hold:", "Repeat while ", "Contract: ", "Receipt: ")


class LoopBlock:
    """A packet's Until Loop block cut into the parts a cold reader acts on (shiploop_loops.invoke_lines).

    ``lines`` run from the block's heading to its closing rule (to the packet's last line when it has none), and
    ``start`` is the heading's index in the packet; ``argument`` is what lies between the marker lines; ``exits`` are its
    numbered exit conditions; ``command`` is the literal start line, which comes before the argument; ``result`` is the
    result line.  A part the packet lacks is None (or [] for the argument and the exits), so a test asserts on what is there
    rather than on a parse error.  ``LoopBlock.find`` is None for a packet that prints no block.
    """

    @classmethod
    def find(cls, packet: str) -> Optional["LoopBlock"]:
        """The packet's block, or None when it prints no Until Loop heading (a stage without a loop, a paused packet)."""
        return cls(packet) if any(line.startswith("Until Loop (no iteration limit") for line in packet.splitlines()) else None

    def __init__(self, packet: str) -> None:
        lines = packet.splitlines()
        head = next(i for i, line in enumerate(lines) if line.startswith("Until Loop (no iteration limit"))
        end = next((i for i in range(head, len(lines))
                    if lines[i].startswith(("Call an exit condition satisfied only when", "Unavailable: "))), len(lines) - 1)
        self.start = head
        self.lines = lines[head:end + 1]
        self.begins = [i for i, line in enumerate(self.lines) if line == loops.ARGUMENT_BEGIN]
        self.ends = [i for i, line in enumerate(self.lines) if line == loops.ARGUMENT_END]
        self.argument = (self.lines[self.begins[0] + 1:self.ends[0]] if self.begins and self.ends else [])
        # Decision 20: outside loops.ARGUMENT_STAGES the packet prints no argument, only "Contract: <abs> · Receipt:
        # <abs>"; the argument is the Contract file's (what the loop's own packets state), read here so a test still
        # reasons about the exit conditions.  ``printed_argument`` says which form the packet had.
        self.printed_argument = bool(self.argument)
        files = next((line for line in self.lines if line.startswith("Contract: ") and " · Receipt: " in line), None)
        if not self.argument and files:
            contract_file, receipt = files[len("Contract: "):].split(" · Receipt: ", 1)
            try:
                value = json.loads(Path(contract_file).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                value = None
            if isinstance(value, dict):
                self.argument = ["Work: " + value["work"], ARGUMENT_FIELDS[1], *value["exit_condition"].splitlines(),
                                 value["repeat_condition"], "Contract: " + contract_file, "Receipt: " + receipt]
        outside = self.lines[:self.begins[0]] if self.begins else self.lines
        commands = [line for line in outside if line.startswith("python3 ") and " start --receipt " in line]
        self.command: Optional[str] = commands[0] if commands else None
        self.result = next((line for line in self.lines if line.startswith("Result: ")), None)

    @property
    def exits(self) -> list[str]:
        """The numbered exit conditions as printed ("1. <condition>"): the argument lines between the "Exit when ALL of
        these hold:" line and the next field."""
        opening = next((i for i, line in enumerate(self.argument) if line.startswith(ARGUMENT_FIELDS[1])), None)
        if opening is None:
            return []
        found: list[str] = []
        for line in self.argument[opening + 1:]:
            if line.startswith(ARGUMENT_FIELDS[2:]):
                break
            found.append(line)
        return found

    def field(self, label: str) -> str:
        """The argument line that opens the field ``label`` (without the label for Contract and Receipt)."""
        found = [line for line in self.argument if line.startswith(label)]
        if len(found) != 1:
            raise AssertionError(f"{label!r} opens {len(found)} argument lines, not one")
        return found[0][len(label):] if label in ("Contract: ", "Receipt: ") else found[0]

    def run(self, cwd: Path) -> dict[str, Any]:
        """Run the printed start command in a shell, as every host does; return the packet it prints."""
        done = subprocess.run(self.command, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=60)
        if done.returncode:
            raise RuntimeError("the printed start command failed: " + done.stderr + done.stdout)
        return json.loads(done.stdout)
