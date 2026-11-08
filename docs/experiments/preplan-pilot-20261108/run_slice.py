"""Use the established slice runner with this pilot's frozen cases and fixtures.

Only the fixture catalog and fixture root are injected. The runner, stop logic,
host adapter, engine callbacks, Improve and exported measurements are unchanged.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
import slice as runner

runner.STEP_CASES = HERE / "cases.json"
runner.FIXTURES = HERE / "fixtures"

if __name__ == "__main__":
    raise SystemExit(runner.main())
