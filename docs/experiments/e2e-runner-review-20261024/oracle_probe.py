"""E2: do today's case checks (origin/main) still pass the audit's broken Battleship server? Uses run.run_checks."""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import run
work = Path(sys.argv[2]); case = sys.argv[3]
checks = json.loads((Path(sys.argv[1]) / "cases.json").read_text())[case]["checks"]
res = run.run_checks(work, checks, timeout=120)
print(json.dumps([{"check": i + 1, "returncode": r.get("returncode"), "passed": r.get("returncode") == 0} for i, r in enumerate(res)]))
