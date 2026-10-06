"""The test-author probe judge, the first design against the corrected one, on seven recorded outputs.

The first design judged every exit code in red mode and accepted `red` and `green`; an exit-0 run that ran
nothing then passed. The corrected judge, which the repository now runs (shiploop_test_loop.verify at
PROBE_STAGE), judges exit 0 in passing mode and a non-zero exit in red mode, and accepts `passed` and `red`.
Run: python3 -B probe_judge.py   (reads the shipped judge from this checkout; writes nothing)
The same rows are pinned as PROBE_CASES in test/shiploop-test-loop.test.py; this file keeps the comparison."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_test_loop as tl

focused = {"suite": "focused", "command": "x", "ids": []}
focused_ids = {"suite": "focused", "command": "x", "ids": ["T1"]}
node_missing = "node:internal/modules/cjs/loader:1228\n  throw err;\nError: Cannot find module './rules'\nNode.js v22\n"
unittest_ok = "..\nRan 2 tests in 0.001s\n\nOK\n"
unittest_fail = "F.\n======\nFAIL: test_a\nRan 2 tests in 0.001s\n\nFAILED (failures=1)\n"
unittest_zero = "\nRan 0 tests in 0.000s\n\nOK\n"
cases = [
    ("exit0 empty output", focused, 0, ""),
    ("exit0 ids listed never shown", focused_ids, 0, "all good\n"),
    ("exit0 ran 2", focused, 0, unittest_ok),
    ("exit0 ran 0", focused, 0, unittest_zero),
    ("exit1 node missing module, no ids", focused, 1, node_missing),
    ("exit1 node missing module, ids listed", focused_ids, 1, node_missing),
    ("exit1 one failing test", focused, 1, unittest_fail),
]


def draft_probe(row, code, out):  # the first design: red mode for every exit code, good = red, green
    verdict = tl.judge(row, code, out, red=True)
    return verdict["status"], verdict["status"] in ("red", "green")


def fixed_probe(row, code, out):  # the corrected design: passing mode on exit 0, red mode otherwise
    verdict = tl.judge(row, code, out, red=(code != 0))
    return verdict["status"], verdict["status"] in ("red", "passed")


for name, row, code, out in cases:
    first, fixed = draft_probe(row, code, out), fixed_probe(row, code, out)
    print(f"{name:42s} first={first[0]:11s} accepted={first[1]!s:5s} | corrected={fixed[0]:11s} accepted={fixed[1]}")
