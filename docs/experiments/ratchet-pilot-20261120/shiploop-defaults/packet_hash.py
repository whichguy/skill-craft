"""sha256 and size of each planning packet as printed at the head-order suite's reference install, for the checkout at argv[1]."""
import hashlib, importlib.util, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "test"))
import state_home
state_home.isolate()
spec = importlib.util.spec_from_file_location("head_order", root / "test" / "shiploop-head-order.test.py")
m = importlib.util.module_from_spec(spec); sys.modules["head_order"] = m; spec.loader.exec_module(m)
rows = m.renders("inline", m.INSTALL_RUN_DIR)
for key, row in rows.items():
    stage = m.plans.stage_of(key)
    if stage in ("spec", "test-strategy") and "printed" in row and "improve" not in str(key):
        text = row["printed"]
        print(stage, len(text), hashlib.sha256(text.encode()).hexdigest()[:16])
