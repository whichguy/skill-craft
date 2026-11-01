#!/usr/bin/env python3
"""HTTP probes for the own checks of chain B's cases (`user-roles`, `user-team-listing`, `user-page-size`), run by serve.py against the delivered server.

    python3 "$E2E_CHECKS/serve.py" --start "node src/server.js" -- python3 "$E2E_CHECKS/user_directory_probe.py" MODE

serve.py puts the server's address in BASE. A mode prints one ``FAIL:`` line for each expectation that does not hold and exits 1, or exits 0.
The store is the base's three users (Ada Lovelace 1, Grace Hopper 2, Alan Turing 3) and, from `user-team-listing` on, the five teams of its request.
No mode reads a rule an earlier request set and a later one replaces: a case's own checks run again as the regression of every later
link, so `user-roles` and `user-team-listing` use explicit sizes only (the default page size and the largest size are `user-page-size`'s).

* ``roles``, ``combine``, ``badrole``: `user-roles`.
* ``teams``, ``teamsfilter``, ``teamspage``: `user-team-listing`.
* ``sizedefault``, ``sizesetting`` (run with PAGE_SIZE=2), ``sizelargest``: `user-page-size`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

CALL_SECONDS = 5


def get(path: str) -> tuple[int, object]:
    """One GET against the delivered server: the status and the parsed JSON body (None when the body is not JSON)."""
    try:
        with urllib.request.urlopen(os.environ["BASE"] + path, timeout=CALL_SECONDS) as reply:
            status, raw = reply.status, reply.read()
    except urllib.error.HTTPError as error:
        with error:
            status, raw = error.code, error.read()
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, None


def ids(body) -> object:
    """The ids of a list of records; the body itself when it is not one."""
    return [item.get("id") for item in body if isinstance(item, dict)] if isinstance(body, list) else body


def page_of(body) -> object:
    """A page object as (page, size, total, pages, ids of its items); the body itself when it is not one."""
    if isinstance(body, dict) and all(key in body for key in ("page", "size", "total", "pages", "items")):
        return body["page"], body["size"], body["total"], body["pages"], ids(body["items"])
    return body


def refused(status: int, body) -> bool:
    """A 400 with a JSON object whose "error" is a text, and no records."""
    return status == 400 and isinstance(body, dict) and isinstance(body.get("error"), str) and bool(body["error"].strip()) and "items" not in body


class Probe:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def listing(self, path: str, want: list) -> None:
        status, body = get(path)
        if status != 200 or ids(body) != want:
            self.failures.append(f"{path}: HTTP {status}, ids {ids(body)}, wanted {want}")

    def page(self, path: str, want: tuple) -> None:
        status, body = get(path)
        if status != 200 or page_of(body) != want:
            self.failures.append(f"{path}: HTTP {status}, {page_of(body)}, wanted {want}")

    def bad(self, path: str) -> None:
        status, body = get(path)
        if not refused(status, body):
            self.failures.append(f"{path}: HTTP {status} {json.dumps(body)[:80]}, wanted 400 with an error and no records")

    def check(self, label: str, ok: bool, got: object = None) -> None:
        if not ok:
            self.failures.append(f"{label}: {json.dumps(got)[:120]}")

    def done(self) -> int:
        for line in self.failures:
            print("FAIL: " + line)
        return 1 if self.failures else 0


def roles(p: Probe) -> None:
    status, user = get("/users/1")
    p.check("/users/1 shows role admin", status == 200 and isinstance(user, dict) and user.get("role") == "admin", user)
    status, everyone = get("/users")
    p.check("/users shows each role", status == 200 and isinstance(everyone, list) and [u.get("role") for u in everyone] == ["admin", "member", "viewer"], everyone)
    p.listing("/users?role=member", [2])
    p.listing("/users?role=admin", [1])
    status, body = get("/users?page=1&size=3")
    p.check("a page shows each role", status == 200 and isinstance(body, dict) and [u.get("role") for u in body.get("items") or []] == ["admin", "member", "viewer"], body)


def combine(p: Probe) -> None:
    p.listing("/users?name=a&role=viewer", [3])
    p.listing("/users?name=a&role=admin", [1])
    p.listing("/users?name=grace&role=admin", [])
    p.listing("/users?name=&role=member", [2])
    p.page("/users?role=viewer&page=1&size=1", (1, 1, 1, 1, [3]))
    p.page("/users?name=a&role=member&page=1&size=2", (1, 2, 1, 1, [2]))
    p.page("/users?name=alan&role=member&page=1&size=2", (1, 2, 0, 0, []))


def bad_role(p: Probe) -> None:
    for query in ("role=owner", "role=", "role=root&page=1&size=2", "role=admin&page=0"):
        p.bad(f"/users?{query}")


def teams(p: Probe) -> None:
    status, everyone = get("/teams")
    names = [t.get("name") for t in everyone] if isinstance(everyone, list) else everyone
    members = [t.get("members") for t in everyone] if isinstance(everyone, list) else everyone
    p.check("/teams lists the five teams in id order, with their members", status == 200 and ids(everyone) == [1, 2, 3, 4, 5]
            and names == ["Analytical Engine", "Compilers", "Computing Machinery", "Cryptanalysis", "Data Systems"]
            and members == [[1], [2], [3], [3], [1, 2]], everyone)
    status, one = get("/teams/5")
    p.check("/teams/5 shows its name and members", status == 200 and isinstance(one, dict) and one.get("name") == "Data Systems"
            and one.get("members") == [1, 2], one)
    for path in ("/teams/99", "/teams/0"):
        status, body = get(path)
        p.check(f"{path} is a 404 with an error", status == 404 and isinstance(body, dict) and isinstance(body.get("error"), str), body)


def teams_filter(p: Probe) -> None:
    p.listing("/teams?name=COMP", [2, 3])
    p.listing("/teams?name=an", [1, 4])
    p.listing("/teams?name=a.a", [])
    p.listing("/teams?name=(", [])
    p.listing("/teams?name=", [1, 2, 3, 4, 5])
    p.listing("/teams?name=zzz", [])
    p.listing("/teams?sort=name&_=1", [1, 2, 3, 4, 5])


def teams_page(p: Probe) -> None:
    p.page("/teams?page=2&size=2", (2, 2, 5, 3, [3, 4]))
    p.page("/teams?page=3&size=2", (3, 2, 5, 3, [5]))
    p.page("/teams?page=4&size=2", (4, 2, 5, 3, []))
    p.page("/teams?name=comp&page=2&size=1", (2, 1, 2, 2, [3]))
    p.page("/teams?name=zzz&page=1&size=5", (1, 5, 0, 0, []))
    for query in ("page=0", "page=1.5", "page=", "size=0", "size=abc", "size=", "size=101"):
        p.bad(f"/teams?{query}")


def size_default(p: Probe) -> None:
    p.page("/users?page=1", (1, 25, 3, 1, [1, 2, 3]))
    p.page("/teams?page=1", (1, 25, 5, 1, [1, 2, 3, 4, 5]))
    p.page("/users?size=2", (1, 2, 3, 2, [1, 2]))


def size_setting(p: Probe) -> None:
    p.page("/users?page=1", (1, 2, 3, 2, [1, 2]))
    p.page("/users?page=2", (2, 2, 3, 2, [3]))
    p.page("/teams?page=3", (3, 2, 5, 3, [5]))
    p.page("/users?size=3", (1, 3, 3, 1, [1, 2, 3]))
    p.listing("/users", [1, 2, 3])
    p.listing("/teams", [1, 2, 3, 4, 5])


def size_largest(p: Probe) -> None:
    p.page("/users?size=50", (1, 50, 3, 1, [1, 2, 3]))
    p.page("/teams?size=50", (1, 50, 5, 1, [1, 2, 3, 4, 5]))
    for path in ("/users?size=51", "/users?size=100", "/teams?size=51", "/teams?size=100"):
        p.bad(path)


MODES = {"roles": roles, "combine": combine, "badrole": bad_role, "teams": teams, "teamsfilter": teams_filter, "teamspage": teams_page,
         "sizedefault": size_default, "sizesetting": size_setting, "sizelargest": size_largest}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in MODES:
        print(f"usage: user_directory_probe.py {{{'|'.join(MODES)}}}", file=sys.stderr)
        return 2
    probe = Probe()
    MODES[argv[0]](probe)
    return probe.done()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
