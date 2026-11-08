"""Small public case checks. Inventory retention is not semantic AD conformity."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request


def api():
    base = os.environ["BASE"]
    with urllib.request.urlopen(base + "/") as response:
        assert response.status == 200
        assert "roundtable" in response.read().decode().lower(), "Roundtable page absent"
    for text, expected_status in (("@Scribe outline the launch", 200), (" \n ", 400)):
        request = urllib.request.Request(base + "/api/agent", data=json.dumps({"text": text}).encode(),
                                         headers={"content-type": "application/json"}, method="POST")
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status == expected_status, (text, response.status)
            if expected_status == 200:
                assert json.load(response) == {"text": "Demo reply: " + text}
    print("page and real local agent endpoint passed")


def knowledge():
    prior = Path(os.environ["PRIOR_WORK"])
    for name, prefix in (("spec.md", "R"), ("architecture.md", "AD")):
        relative = Path("docs/shiploop") / name
        before = (prior / relative).read_text()
        after = relative.read_text()
        pattern = rf"\b{prefix}-\d+\b"
        old_ids, new_ids = set(re.findall(pattern, before)), set(re.findall(pattern, after))
        assert old_ids, f"predecessor has no {prefix} IDs"
        assert old_ids <= new_ids, f"missing earlier {prefix} IDs: {sorted(old_ids - new_ids)}"
    print("requirement/decision IDs retained; meanings and justified amendments need semantic review")


COMMANDS = {"api": api, "knowledge": knowledge}
if __name__ == "__main__":
    COMMANDS[sys.argv[1]]()
