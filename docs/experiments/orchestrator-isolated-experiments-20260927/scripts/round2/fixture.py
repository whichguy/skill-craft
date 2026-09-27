"""Import the snapshot's own ShipLoop fixture driver."""
import importlib.util, sys
from pathlib import Path
EXP = Path(__file__).resolve().parents[1]
SRC = EXP / "src"
spec = importlib.util.spec_from_file_location("tl", SRC / "test/shiploop-test-loop.test.py")
tl = importlib.util.module_from_spec(spec); sys.modules["tl"] = tl; spec.loader.exec_module(tl)
nav, store, test_loop, git = tl.nav, tl.store, tl.test_loop, tl.git
import shiploop_stage_spec as stage_spec  # noqa  (path set by tl)
