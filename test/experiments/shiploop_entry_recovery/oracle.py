#!/usr/bin/env python3
"""Fixed outcome checks for the opt-in locator-only recovery fixture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy

CASES = (
    ("", []),
    (" \t\n  ", []),
    (" a \n \n b\n a ", ["a", "b", "a"]),
    (" x\r\ny \r\n", ["x", "y"]),
    ("\u2003hello\u2003\n\u2003", ["hello"]),
    ("# keep\n x y ", ["# keep", "x y"]),
    ("one\v two\fthree", ["one", "two", "three"]),
)
INVALID = (None, 1, True, [], b"x")


def grade(source: Path) -> dict:
    function = runpy.run_path(str(source))["clean_lines"]
    observations = []
    for value, expected in CASES:
        try:
            actual = function(value)
            observations.append({"case": repr(value), "passed": actual == expected,
                                 "expected": expected, "actual": actual})
        except Exception as error:
            observations.append({"case": repr(value), "passed": False,
                                 "error": type(error).__name__})
    for value in INVALID:
        try:
            function(value)
            actual = "no exception"
        except Exception as error:
            actual = type(error).__name__
        observations.append({"case": repr(value), "passed": actual == "TypeError",
                             "expected": "TypeError", "actual": actual})
    return {"passed": sum(row["passed"] for row in observations),
            "total": len(observations), "observations": observations}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    result = grade(args.source)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
