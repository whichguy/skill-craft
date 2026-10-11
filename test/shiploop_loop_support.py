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
from typing import Any, Mapping

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
