"""Run the hermetic ShipLoop security tests registered in the suite catalog."""

from pathlib import Path
import sys
import unittest


def main() -> int:
    sys.dont_write_bytecode = True
    directory = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(str(directory), pattern="test*.py")
    if suite.countTestCases() == 0:
        print(f"No tests discovered in {directory}", file=sys.stderr)
        return 1
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
