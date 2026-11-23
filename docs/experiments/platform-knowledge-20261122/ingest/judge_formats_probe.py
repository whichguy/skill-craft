"""Feed ShipLoop's test judge one saved sample of each `sf apex run test` output format.

Usage: PYTHONDONTWRITEBYTECODE=1 python3 -I judge_formats_probe.py SHIPLOOP_SCRIPTS_DIR

The two samples are trimmed copies of real output saved in the run
chess-sf-full-12a23d (2026-10-25): the human table from a verify record and the
tap stream from a check-only record, with the org user name removed. The probe
prints what `shiploop_test_counts` reads from each and the status
`shiploop_test_loop.judge` gives a focused command, the way a step plan records
one, under each format. It calls no model and runs no command.
"""

from __future__ import annotations

import importlib
import json
import sys

HUMAN = """=== Test Results
TEST NAME                                  OUTCOME  MESSAGE  RUNTIME (MS)
─────────────────────────────────────────  ───────  ───────  ────────────
SLChessRulesTest.TC_10_epCapture           Pass              52
SLChessRulesTest.TC_19_controllerMates     Pass              128
SLChessRulesTest.TC_1_startFen             Pass              17
SLChessRulesTest.TC_2_startLegalMoves      Pass              54


=== Test Summary
NAME                 VALUE
───────────────────  ──────
Outcome              Passed
Tests Ran            4
Pass Rate            100%
"""
TAP = """1..4
ok 1 SLChessRulesTest.TC_10_epCapture
ok 2 SLChessRulesTest.TC_19_controllerMates
ok 3 SLChessRulesTest.TC_1_startFen
ok 4 SLChessRulesTest.TC_2_startLegalMoves
# Run "sf apex get test -i  -o <user> --result-format <format>" to retrieve test results in a different format.
"""
IDS = ["TC_1_startFen", "TC_19_controllerMates"]


def failing(text: str) -> str:
    """The same output with TC_1_startFen failed, in that format's own words."""
    return text.replace(
        "TC_1_startFen             Pass", "TC_1_startFen             Fail"
    ).replace(
        "ok 3 SLChessRulesTest.TC_1_startFen", "not ok 3 SLChessRulesTest.TC_1_startFen"
    )


def main() -> int:
    sys.path.insert(0, sys.argv[1])
    counts = importlib.import_module("shiploop_test_counts")
    loop = importlib.import_module("shiploop_test_loop")
    for name, text in (("human", HUMAN), ("tap", TAP)):
        print("==", name)
        print("  count:", json.dumps(counts.count(text, 0)))
        print("  outcomes:", json.dumps(counts.outcomes(text, IDS)))
        cases = (
            ("focused, ids listed, exit 0", {"suite": "focused", "ids": IDS}, 0, text),
            ("focused, no ids, exit 0", {"suite": "focused"}, 0, text),
            (
                "focused, ids, one test failed, exit 1",
                {"suite": "focused", "ids": IDS},
                1,
                failing(text),
            ),
            (
                "focused, ids, one test failed, exit 0",
                {"suite": "focused", "ids": IDS},
                0,
                failing(text),
            ),
        )
        for label, row, code, output in cases:
            print("  " + label + ":", loop.judge(row, code, output)["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
