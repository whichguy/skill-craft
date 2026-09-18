#!/usr/bin/env python3
"""Hermetic probe-decision fixture and study checks; never launch a model."""
from pathlib import Path
import unittest


if __name__ == "__main__":
    root = Path(__file__).resolve().parent / "experiments" / "shiploop_probe_decisions"
    suite = unittest.defaultTestLoader.discover(str(root), pattern="test_*.py")
    if not suite.countTestCases():
        raise SystemExit("probe-decision test inventory is empty")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
