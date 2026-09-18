#!/usr/bin/env python3
"""Stdlib unittest selector used by this fixture."""
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent

class DiscoveryError(Exception):
    """A discovery failure must not disappear when selecting a subset."""

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def discovered():
    loader = unittest.TestLoader()
    tests = list(flatten(loader.discover(str(ROOT), pattern="test_*.py", top_level_dir=str(ROOT))))
    if loader.errors:
        raise DiscoveryError("\n".join(loader.errors))
    return tests

def tags(test):
    method = getattr(test, getattr(test, "_testMethodName", ""), None)
    return frozenset(getattr(method, "__shiploop_suites__", getattr(type(test), "__shiploop_suites__", ())))

def selected(tests, suite):
    return tests if suite == "full" else [test for test in tests if suite in tags(test)]

def selections():
    tests = discovered()
    return {name: [test.id() for test in selected(tests, name)] for name in ("focused", "smoke", "full")}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("focused", "smoke", "full"))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1 or not args.suite and not args.list:
        parser.error("choose --list or --suite and use a positive --repeat")
    try:
        listed = selections()
    except DiscoveryError as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.list:
        print(json.dumps(listed, sort_keys=True))
        if not args.suite:
            return 0
    selected_ids = listed[args.suite]
    if not selected_ids:
        print(f"no tests selected for suite {args.suite}", file=sys.stderr)
        return 1
    print("SHIPLOOP_SELECTION=" + json.dumps({"suite": args.suite, "ids": selected_ids, "repeat": args.repeat, "reverse": args.reverse}))
    ok = True
    for _ in range(args.repeat):
        try:
            tests = selected(discovered(), args.suite)
        except DiscoveryError as error:
            print(str(error), file=sys.stderr)
            return 1
        if not tests:
            print(f"no tests selected for suite {args.suite}", file=sys.stderr)
            return 1
        if args.reverse:
            tests.reverse()
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.TestSuite(tests))
        ok = ok and result.wasSuccessful()
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
