#!/usr/bin/env python3
"""Offline real-Git and evidence tests for parallel Ask Agent experiments."""
from pathlib import Path
import unittest

if __name__ == '__main__':
    tests=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'experiments/ask_agent_parallel_worktrees'),pattern='test_*.py')
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(tests).wasSuccessful() else 1)
