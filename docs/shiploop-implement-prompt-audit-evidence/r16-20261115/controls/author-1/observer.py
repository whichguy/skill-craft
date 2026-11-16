import json, sys
from pathlib import Path
target, expected, claim, rigged = sys.argv[1:]
try:
    value = json.loads(Path(target).read_text())
    observed = value["candidate"]
    state = "requested candidate present" if observed == expected else "different revision"
    passed = {"identity": observed == expected, "presence": True,
              "behavior": value["behavior"] == "ready"}[claim]
    code = 0 if passed else 1
except FileNotFoundError:
    state, observed, code = "absent", None, 1
except (OSError, ValueError, KeyError, TypeError):
    state, observed, code = "indeterminate", None, 2
if rigged == "always-success":
    code = 0
print(json.dumps({"state": state, "requested": expected, "observed": observed,
                  "claim": claim}))
sys.exit(code)
