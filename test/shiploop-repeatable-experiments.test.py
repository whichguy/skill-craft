#!/usr/bin/env python3
"""Hermetic repeatable-test pilot checks; never launch models or remote calls."""
from pathlib import Path
import unittest


if __name__ == '__main__':
    root = Path(__file__).resolve().parent / 'experiments' / 'shiploop_repeatable_tests'
    if (root / 'samples' / '__init__.py').exists():
        raise SystemExit('observed RED samples must remain outside apparatus discovery')
    suite = unittest.defaultTestLoader.discover(str(root), pattern='test_*.py')
    if not suite.countTestCases():
        raise SystemExit('repeatable-test experiment inventory is empty')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
