#!/usr/bin/env python3
"""Hermetic checks for the experimental discovery apparatus; never launch a model."""
from pathlib import Path
import unittest


if __name__ == "__main__":
    root = Path(__file__).resolve().parent / "experiments" / "shiploop_generalized_discovery"
    suite = unittest.defaultTestLoader.discover(str(root), pattern="test_*.py")
    if not suite.countTestCases():
        raise SystemExit("generalized discovery test inventory is empty")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
