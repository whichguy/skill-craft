#!/usr/bin/env python3
"""Product checks for the `shared-expenses` case (style: stateful-service).

Run from the case's work directory: `python3 expense_service.py <check>`. Each check
starts `node server.js` with its own PORT and a DATA_FILE in a temporary directory,
exercises the HTTP contract the case prompt states, stops the server, and exits 0
on pass. Nothing is written into the work directory. The concurrency check asserts
an invariant (every expense recorded once, the balances exact, all of it still
there after a restart), not timing, so it cannot flake on a correct service.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import contextlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def server(data_file: Path):
    port = free_port()
    env = dict(os.environ, PORT=str(port), DATA_FILE=str(data_file))
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(["node", "server.js"], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=errors)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    errors.seek(0)
                    fail("server.js exited early: " + errors.read().decode(errors="replace")[-400:])
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                fail("server.js did not listen on PORT within 10 seconds")
            yield f"http://127.0.0.1:{port}"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def call(base: str, method: str, path: str, body: object = None) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except ValueError:
            return error.code, None


def expect(got: tuple[int, object], status: int, what: str, **fields) -> object:
    code, body = got
    if code != status:
        fail(f"{what}: want HTTP {status}, got {code} {body}")
    for key, value in fields.items():
        if not isinstance(body, dict) or body.get(key) != value:
            fail(f"{what}: want {key}={value}, got {body}")
    return body


def create(base: str, group: str, members: list[str]) -> None:
    expect(call(base, "POST", "/groups", {"id": group, "members": members}), 201, f"create {group}")


# What the prompt's rules give, written down again here so that a check compares a service with the rules and not with itself.
def equal_shares(members: list[str], cents: int) -> dict[str, int]:
    base, extra = divmod(cents, len(members))
    return {name: base + (1 if index < extra else 0) for index, name in enumerate(members)}


def net_balances(members: list[str], expenses: list[tuple[str, int, dict[str, int]]]) -> dict[str, int]:
    net = {name: 0 for name in members}
    for payer, cents, owed in expenses:
        net[payer] += cents
        for name, amount in owed.items():
            net[name] -= amount
    return net


def payments_for(members: list[str], net: dict[str, int]) -> list[dict]:
    net = dict(net)
    payments = []
    while True:
        debtors = [name for name in members if net[name] < 0]
        creditors = [name for name in members if net[name] > 0]
        if not debtors or not creditors:
            return payments
        debtor = min(debtors, key=lambda name: (net[name], members.index(name)))
        creditor = max(creditors, key=lambda name: (net[name], -members.index(name)))
        cents = min(-net[debtor], net[creditor])
        payments.append({"from": debtor, "to": creditor, "cents": cents})
        net[debtor] += cents
        net[creditor] -= cents


def unit() -> None:
    done = subprocess.run(["node", "--test"], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    passed = re.search(r"^(?:ℹ|#) pass (\d+)", done.stdout + done.stderr, re.M)
    if done.returncode != 0 or not passed or int(passed.group(1)) < 1:
        fail("node --test must pass and run at least one test:\n" + (done.stdout + done.stderr)[-800:])


def contract() -> None:
    members = ["ann", "bob", "cy"]
    path = "/groups/trip/expenses"
    with tempfile.TemporaryDirectory() as tmp, server(Path(tmp) / "data.json") as base:
        create(base, "trip", members)
        expect(call(base, "POST", "/groups", {"id": "trip", "members": ["dan", "eve"]}), 409, "duplicate id")
        for bad in ([], ["ann"], ["ann", "ann"], ["ann", ""], ["ann", 5], "ann,bob", None):
            expect(call(base, "POST", "/groups", {"id": "bad", "members": bad}), 400, f"members {bad!r}")
        expect(call(base, "POST", "/groups", {"id": "bad"}), 400, "no members")
        create(base, "bad", ["dan", "eve"])

        rejected = [
            ("/groups/none/expenses", {"payer": "ann", "cents": 100, "split": "equal"}, 404, "unknown group"),
            (path, {"payer": "dan", "cents": 100, "split": "equal"}, 400, "unknown payer"),
            (path, {"cents": 100, "split": "equal"}, 400, "no payer"),
            (path, {"payer": "ann", "cents": 0, "split": "equal"}, 400, "zero cents"),
            (path, {"payer": "ann", "cents": -5, "split": "equal"}, 400, "negative cents"),
            (path, {"payer": "ann", "cents": 10.5, "split": "equal"}, 400, "fractional cents"),
            (path, {"payer": "ann", "cents": "10", "split": "equal"}, 400, "cents as text"),
            (path, {"payer": "ann", "split": "equal"}, 400, "no cents"),
            (path, {"payer": "ann", "cents": 100, "split": "thirds"}, 400, "unknown split"),
            (path, {"payer": "ann", "cents": 100, "split": "exact"}, 400, "exact without shares"),
            (path, {"payer": "ann", "cents": 100, "split": "exact", "shares": {"ann": 50, "bob": 40}}, 400, "shares short"),
            (path, {"payer": "ann", "cents": 100, "split": "exact", "shares": {"ann": 60, "bob": 50}}, 400, "shares over"),
            (path, {"payer": "ann", "cents": 100, "split": "exact", "shares": {"ann": 110, "bob": -10}}, 400, "negative share"),
            (path, {"payer": "ann", "cents": 100, "split": "exact", "shares": {"ann": 50.5, "bob": 49.5}}, 400, "fractional shares"),
            (path, {"payer": "ann", "cents": 100, "split": "exact", "shares": {"ann": 50, "dan": 50}}, 400, "share of a stranger"),
        ]
        for target, body, status, what in rejected:
            expect(call(base, "POST", target, body), status, what)
        expect(call(base, "GET", "/groups/trip/balances"), 200, "balances after rejections", ann=0, bob=0, cy=0)
        expect(call(base, "GET", "/groups/trip/settlements"), 200, "no settlements after rejections")
        if call(base, "GET", "/groups/trip/settlements")[1] != []:
            fail("settlements of a group with nothing owed: want []")
        expect(call(base, "POST", path, {"payer": "ann", "cents": 90, "split": "equal"}), 201, "first expense", expense=1)
        expect(call(base, "POST", path, {"payer": "bob", "cents": 30, "split": "exact", "shares": {"cy": 30}}), 201,
               "second expense, after rejections that took no number", expense=2)
        for route in ("balances", "settlements"):
            expect(call(base, "GET", f"/groups/none/{route}"), 404, f"{route} of an unknown group")


def split() -> None:
    members = ["ann", "bob", "cy", "dee"]
    with tempfile.TemporaryDirectory() as tmp, server(Path(tmp) / "data.json") as base:
        create(base, "g", members)
        recorded: list[tuple[str, int, dict[str, int]]] = []
        sequence = 0
        for payer, cents in (("ann", 1), ("bob", 2), ("cy", 3), ("dee", 5), ("ann", 10), ("bob", 11), ("cy", 99), ("dee", 100),
                             ("ann", 101), ("bob", 102), ("cy", 103), ("dee", 1000001)):
            sequence += 1
            expect(call(base, "POST", "/groups/g/expenses", {"payer": payer, "cents": cents, "split": "equal"}), 201,
                   f"equal split of {cents}", expense=sequence)
            recorded.append((payer, cents, equal_shares(members, cents)))
            expect(call(base, "GET", "/groups/g/balances"), 200, f"balances after an equal split of {cents}",
                   **net_balances(members, recorded))
        for payer, cents, shares in (("ann", 90, {"bob": 30, "cy": 60}), ("bob", 50, {"ann": 10, "bob": 20, "cy": 20}),
                                     ("cy", 70, {"cy": 70}), ("dee", 40, {"ann": 0, "bob": 40})):
            sequence += 1
            expect(call(base, "POST", "/groups/g/expenses", {"payer": payer, "cents": cents, "split": "exact", "shares": shares}),
                   201, f"exact split of {cents}", expense=sequence)
            recorded.append((payer, cents, shares))
            expect(call(base, "GET", "/groups/g/balances"), 200, f"balances after an exact split of {cents}",
                   **net_balances(members, recorded))
        total = sum(call(base, "GET", "/groups/g/balances")[1].values())
        if total != 0:
            fail(f"balances must add up to 0, got {total}")


def settle() -> None:
    with tempfile.TemporaryDirectory() as tmp, server(Path(tmp) / "data.json") as base:
        def pay(group: str, payer: str, cents: int, shares: dict[str, int] | None = None) -> None:
            body = {"payer": payer, "cents": cents, "split": "equal"} if shares is None else \
                {"payer": payer, "cents": cents, "split": "exact", "shares": shares}
            expect(call(base, "POST", f"/groups/{group}/expenses", body), 201, f"{group}: {payer} pays {cents}")

        def settlements(group: str) -> list:
            code, body = call(base, "GET", f"/groups/{group}/settlements")
            if code != 200 or not isinstance(body, list):
                fail(f"{group}: settlements: want HTTP 200 and a JSON array, got {code} {body}")
            return body

        create(base, "idle", ["ann", "bob"])
        if settlements("idle") != []:
            fail("a group with nothing owed settles with []")

        create(base, "debtors", ["ann", "bob", "cy", "dee"])
        pay("debtors", "ann", 400)
        want = [{"from": "bob", "to": "ann", "cents": 100}, {"from": "cy", "to": "ann", "cents": 100},
                {"from": "dee", "to": "ann", "cents": 100}]
        if settlements("debtors") != want:
            fail(f"owing the same amount, the member listed first pays first: want {want}, got {settlements('debtors')}")

        create(base, "creditors", ["ann", "bob", "cy"])
        pay("creditors", "bob", 100, {"ann": 100})
        pay("creditors", "cy", 100, {"ann": 100})
        want = [{"from": "ann", "to": "bob", "cents": 100}, {"from": "ann", "to": "cy", "cents": 100}]
        if settlements("creditors") != want:
            fail(f"owed the same amount, the member listed first is paid first: want {want}, got {settlements('creditors')}")

        create(base, "mixed", ["ann", "bob", "cy"])
        pay("mixed", "ann", 100)
        pay("mixed", "bob", 50, {"ann": 10, "bob": 20, "cy": 20})
        want = [{"from": "cy", "to": "ann", "cents": 53}, {"from": "bob", "to": "ann", "cents": 3}]
        if settlements("mixed") != want:
            fail(f"largest debt pays the largest credit: want {want}, got {settlements('mixed')}")

        members = ["ann", "bob", "cy", "dee", "eve", "fay"]
        create(base, "big", members)
        recorded = []
        for index, (payer, cents) in enumerate((("ann", 1299), ("bob", 4510), ("cy", 777), ("dee", 3001), ("eve", 250), ("fay", 9999),
                                                ("ann", 31), ("cy", 1200))):
            pay("big", payer, cents)
            recorded.append((payer, cents, equal_shares(members, cents)))
        pay("big", "dee", 600, {"ann": 100, "eve": 200, "fay": 300})
        recorded.append(("dee", 600, {"ann": 100, "eve": 200, "fay": 300}))
        net = net_balances(members, recorded)
        got = settlements("big")
        if got != payments_for(members, net):
            fail(f"six members: want {payments_for(members, net)}, got {got}")
        for payment in got:
            net[payment["from"]] += payment["cents"]
            net[payment["to"]] -= payment["cents"]
        if any(net.values()):
            fail(f"the payments must bring every balance to 0, left {net}")


def restart() -> None:
    members = ["ann", "bob", "cy"]
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data.json"
        with server(data) as base:
            create(base, "trip", members)
            expect(call(base, "POST", "/groups/trip/expenses", {"payer": "ann", "cents": 100, "split": "equal"}), 201, "first")
            expect(call(base, "POST", "/groups/trip/expenses",
                        {"payer": "bob", "cents": 50, "split": "exact", "shares": {"ann": 10, "bob": 20, "cy": 20}}), 201, "second")
            expect(call(base, "GET", "/groups/trip/balances"), 200, "before the restart", ann=56, bob=-3, cy=-53)
        with server(data) as base:
            expect(call(base, "GET", "/groups/trip/balances"), 200, "after the restart", ann=56, bob=-3, cy=-53)
            code, body = call(base, "GET", "/groups/trip/settlements")
            if body != [{"from": "cy", "to": "ann", "cents": 53}, {"from": "bob", "to": "ann", "cents": 3}]:
                fail(f"settlements after the restart: got {code} {body}")
            expect(call(base, "POST", "/groups", {"id": "trip", "members": ["dan", "eve"]}), 409, "the group is still there")
            expect(call(base, "POST", "/groups/trip/expenses", {"payer": "cy", "cents": 9, "split": "equal"}), 201,
                   "the next expense after the restart", expense=3)


def concurrency() -> None:
    members = ["ann", "bob", "cy", "dee", "eve"]
    jobs = [(members[index % 5], 7 + index) for index in range(60)]
    expected = net_balances(members, [(payer, cents, equal_shares(members, cents)) for payer, cents in jobs])
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data.json"
        with server(data) as base:
            create(base, "rush", members)
            with ThreadPoolExecutor(max_workers=25) as pool:
                results = list(pool.map(lambda job: call(base, "POST", "/groups/rush/expenses",
                                                         {"payer": job[0], "cents": job[1], "split": "equal"}), jobs))
            codes = [code for code, _ in results]
            if codes != [201] * 60:
                fail(f"60 concurrent expenses: want 60 x 201, got { {c: codes.count(c) for c in set(codes)} }")
            numbers = sorted(body.get("expense") if isinstance(body, dict) else None for _, body in results)
            if numbers != list(range(1, 61)):
                fail(f"60 concurrent expenses: want the numbers 1 to 60 once each, got {numbers}")
            expect(call(base, "GET", "/groups/rush/balances"), 200, "after the rush", **expected)
        with server(data) as base:
            expect(call(base, "GET", "/groups/rush/balances"), 200, "after the rush and a restart", **expected)


CHECKS = {"unit": unit, "contract": contract, "split": split, "settle": settle, "restart": restart, "concurrency": concurrency}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        sys.exit("usage: expense_service.py " + "|".join(CHECKS))
    try:
        CHECKS[sys.argv[1]]()
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        fail(f"{type(exc).__name__}: {exc}")
    print("ok")
