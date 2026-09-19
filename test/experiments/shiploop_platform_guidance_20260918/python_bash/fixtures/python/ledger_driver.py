"""Run a deterministic invariant trace against one Ledger implementation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import random
import sys
from types import ModuleType


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"ledger_fixture_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load fixture: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trace(ledger: object) -> list[str]:
    failures: list[str] = []
    rng = random.Random(20260918)
    for step in range(80):
        account = "alice" if rng.randrange(2) == 0 else "bob"
        delta = rng.randrange(-4, 6)
        before = ledger.snapshot()
        expected = before.get(account, 0) + delta
        try:
            result = ledger.apply(account, delta)
        except ValueError:
            if expected >= 0:
                failures.append(f"step {step}: rejected valid transition")
            if ledger.snapshot() != before:
                failures.append(f"step {step}: rejected transition changed state")
        else:
            if expected < 0:
                failures.append(f"step {step}: accepted invalid transition")
            if result != expected:
                failures.append(f"step {step}: returned {result}, expected {expected}")
        if any(balance < 0 for balance in ledger.snapshot().values()):
            failures.append(f"step {step}: negative balance survived")
    return failures


def main() -> int:
    fixture = Path(sys.argv[1])
    module = load_module(fixture)
    left = module.Ledger()
    right = module.Ledger()
    initial_right = right.snapshot()
    basic_credit_result = left.apply("alice", 7)
    second_instance_isolated = right.snapshot() == initial_right
    before_rejection = left.snapshot()
    try:
        left.apply("alice", -8)
    except ValueError:
        rejected_transition_preserved_state = left.snapshot() == before_rejection
    else:
        rejected_transition_preserved_state = False
    trace_failures = trace(module.Ledger())
    print(
        json.dumps(
            {
                "basic_credit_result": basic_credit_result,
                "second_instance_isolated": second_instance_isolated,
                "rejected_transition_preserved_state": rejected_transition_preserved_state,
                "trace_failures": trace_failures,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
