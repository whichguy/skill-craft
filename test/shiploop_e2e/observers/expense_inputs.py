#!/usr/bin/env python3
"""An observation, never a verdict: what the delivered `shared-expenses` service does with unusual names, ids and sums.

Round 13's blind reading found faults on such input in one delivery of eight, which no case check and no test of the
delivery had caught. This script records the same inputs for any delivery. It changes no check and no verdict; where
the request does not settle the right answer (a name of two spaces, a malformed id answered 400 or 404, a total past
the largest integer a JavaScript number holds exactly) the outcome is recorded and not judged.

It uses the case's own server handling (checks/expense_service.py: a free port, ownership of the listener, a stop by
process group) and writes only into a temporary folder.

Usage: python3 expense_inputs.py DELIVERED_TREE       prints one JSON object
Exit 0 whatever the delivery does; 2 for a usage error; 3 when the observation could not be made (the reason is printed).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "checks"))
import expense_service as service  # noqa: E402  (the server lifecycle and the HTTP call: one implementation)

VERSION = 1
BIG = 9007199254740991   # the largest integer a JavaScript number holds exactly


def raw(base: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=10) as reply:
            return reply.status, reply.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")


def observe(scratch: Path) -> dict:
    out: dict = {"schema": "shiploop-e2e-observation/v1", "observer": "expense-inputs", "version": VERSION}
    call = service.call
    with service.server(scratch / "data.json") as base:
        out["name_of_two_spaces"] = call(base, "POST", "/groups", {"id": "ws", "members": ["ann", "  "]})[0]
        out["id_not_valid_percent_encoding"] = raw(base, "/groups/%E0%A4%A/balances")[0]
        made = call(base, "POST", "/groups", {"id": "__proto__", "members": ["a", "b"]})[0]
        read = raw(base, "/groups/__proto__/balances")[0]
        again = call(base, "POST", "/groups", {"id": "__proto__", "members": ["a", "b"]})[0]
        out["group_id___proto__"] = {"create_read_create": [made, read, again],
                                     "kept": [made, read, again] == [201, 200, 409]}
        call(base, "POST", "/groups", {"id": "pm", "members": ["__proto__", "bob"]})
        call(base, "POST", "/groups/pm/expenses", {"payer": "bob", "cents": 100, "split": "equal"})
        _status, balances = call(base, "GET", "/groups/pm/balances")
        whole = isinstance(balances, dict) and set(balances) == {"__proto__", "bob"} and sum(balances.values()) == 0
        out["member___proto__"] = {"balances": balances, "kept": whole}
        call(base, "POST", "/groups", {"id": "t1", "members": ["x", "2", "d"]})
        for payer in ("x", "2"):
            call(base, "POST", "/groups/t1/expenses", {"payer": payer, "cents": 50, "split": "exact", "shares": {"d": 50}})
        _status, owed = call(base, "GET", "/groups/t1/settlements")
        call(base, "POST", "/groups", {"id": "t2", "members": ["zed", "7", "amy"]})
        call(base, "POST", "/groups/t2/expenses", {"payer": "amy", "cents": 100, "split": "exact",
                                                   "shares": {"zed": 50, "7": 50}})
        _status, owes = call(base, "GET", "/groups/t2/settlements")
        first = lambda rows, key: rows[0].get(key) if isinstance(rows, list) and rows and isinstance(rows[0], dict) else None  # noqa: E731
        out["tie_with_a_numeric_name"] = {"owed_first_to": first(owed, "to"), "owes_first_from": first(owes, "from"),
                                          "listed_first": first(owed, "to") == "x" and first(owes, "from") == "zed"}
        call(base, "POST", "/groups", {"id": "big", "members": ["Ada", "Bo"]})
        one = call(base, "POST", "/groups/big/expenses", {"payer": "Ada", "cents": BIG, "split": "exact", "shares": {"Bo": BIG}})[0]
        two = call(base, "POST", "/groups/big/expenses", {"payer": "Ada", "cents": 2, "split": "exact", "shares": {"Bo": 2}})[0]
        _status, text = raw(base, "/groups/big/balances")
        exact = f'"Ada":{BIG + 2}' in text.replace(" ", "")
        out["total_past_the_largest_exact_integer"] = {
            "statuses": [one, two], "balances": text[:120],
            "result": "exact" if two == 201 and exact else "second expense refused" if two != 201 else "one or more cents off"}
    faults = []
    if out["id_not_valid_percent_encoding"] >= 500:
        faults.append("a server error on a malformed id")
    if not out["group_id___proto__"]["kept"]:
        faults.append("a group id of __proto__ is lost")
    if not out["member___proto__"]["kept"]:
        faults.append("a member named __proto__ is lost")
    if not out["tie_with_a_numeric_name"]["listed_first"]:
        faults.append("a tie goes to a numeric name, not the member listed first")
    out["against_the_request"] = faults
    out["recorded_not_judged"] = {"name_of_two_spaces": out["name_of_two_spaces"],
                                  "id_not_valid_percent_encoding": out["id_not_valid_percent_encoding"],
                                  "total_past_the_largest_exact_integer":
                                      out["total_past_the_largest_exact_integer"]["result"]}
    out["summary"] = "; ".join(faults) if faults else "none of the recorded faults"
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not (Path(argv[0]) / "server.js").is_file():
        print("usage: expense_inputs.py DELIVERED_TREE (a folder holding server.js)", file=sys.stderr)
        return 2
    os.chdir(Path(argv[0]).resolve())   # the case's server helper starts `node server.js` in the working folder
    begun = time.monotonic()
    quiet = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="expense-inputs-") as scratch:
        try:
            with contextlib.redirect_stdout(quiet):
                result = observe(Path(scratch))
        except SystemExit:
            print(json.dumps({"schema": "shiploop-e2e-observation/v1", "observer": "expense-inputs", "version": VERSION,
                              "summary": "not measured: " + " ".join(quiet.getvalue().split())[-300:]}))
            return 3
        except Exception as error:  # an observation that cannot be made is reported, never raised as a product failure
            print(json.dumps({"schema": "shiploop-e2e-observation/v1", "observer": "expense-inputs", "version": VERSION,
                              "summary": "not measured: " + type(error).__name__ + ": " + str(error)[:300]}))
            return 3
    result["seconds"] = round(time.monotonic() - begun, 1)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
