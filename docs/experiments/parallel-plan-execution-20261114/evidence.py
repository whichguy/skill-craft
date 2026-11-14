#!/usr/bin/env python3
"""evidence.py: seeded synthetic access logs and their oracle for the analysis5 fixture (apparatus).

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A5). ``generate(seed, lines)`` returns the
four log files an analysis task reads and the expected answers, computed from the text of each log by an independent reader
(never by the generator's own planting), so the answer is whatever the file says. The oracle lives in the trial folder next to
work/, outside the directory the agents work in, and is read only by the scorer.

  python3 evidence.py [--seed N] [--lines N]      print the expected answers for a seed
  python3 evidence.py --selfcheck                  compare each question's reader with a brute-force one over many seeds

Questions (the wording the plan gives each task is in plans/analysis5.json):
  T1 distinct users with three failed logins (action=login status=fail) whose third is at most 600 s after the first
  T2 the largest number of action=download status=ok events by one user
  T3 distinct ips that appear with status=fail and with status=ok
  T4 the largest gap in seconds between two consecutive events of user u03 (file order is time order)
  T5 the sum of T1 to T4
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import itertools
import random

T0 = datetime(2026, 3, 14, 8, 0, 0, tzinfo=timezone.utc)
USERS = [f"u{n:02d}" for n in range(1, 21)]
ACTIONS = ["login", "logout", "view", "download", "upload"]


def _ts(sec: float) -> str:
    return (T0 + timedelta(seconds=int(sec))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def _parse(text: str) -> list:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        fields = dict(p.split("=", 1) for p in parts[1:])
        rows.append({"t": _epoch(parts[0]), **fields})
    return rows


def q1(text: str) -> int:
    fails: dict = {}
    for r in _parse(text):
        if r["action"] == "login" and r["status"] == "fail":
            fails.setdefault(r["user"], []).append(r["t"])
    return sum(1 for ts in fails.values() if any(ts[i + 2] - ts[i] <= 600 for i in range(len(ts) - 2)))


def q1_brute(text: str) -> int:
    fails: dict = {}
    for r in _parse(text):
        if r["action"] == "login" and r["status"] == "fail":
            fails.setdefault(r["user"], []).append(r["t"])
    return sum(1 for ts in fails.values() if any(c[2] - c[0] <= 600 for c in itertools.combinations(sorted(ts), 3)))


def q2(text: str) -> int:
    counts: dict = {}
    for r in _parse(text):
        if r["action"] == "download" and r["status"] == "ok":
            counts[r["user"]] = counts.get(r["user"], 0) + 1
    return max(counts.values())


def q3(text: str) -> int:
    seen: dict = {}
    for r in _parse(text):
        seen.setdefault(r["ip"], set()).add(r["status"])
    return sum(1 for s in seen.values() if {"fail", "ok"} <= s)


def q4(text: str) -> int:
    times = [r["t"] for r in _parse(text) if r["user"] == "u03"]
    return max(b - a for a, b in zip(times, times[1:]))


def _build(rng: random.Random, lines: int, *, fail_rate: float, plant) -> str:
    """Random events by time, then the planted ones merged in; every line is `time user action status ip`."""
    events = []
    now = 0.0
    ips = [f"10.0.{rng.randint(0, 9)}.{rng.randint(1, 60)}" for _ in range(28)]
    for _ in range(lines):
        now += rng.randint(1, 25)
        action = rng.choices(ACTIONS, weights=[4, 2, 6, 3, 1])[0]
        status = "fail" if action == "login" and rng.random() < fail_rate else "ok"
        events.append((now, rng.choice(USERS), action, status, rng.choice(ips)))
    for item in plant(rng, now, ips):
        events.append(item)
    events.sort(key=lambda e: e[0])
    return "\n".join(f"{_ts(t)} user={u} action={a} status={s} ip={ip}" for t, u, a, s, ip in events) + "\n"


def _plant1(rng, horizon, ips):
    out = []
    users = rng.sample(USERS, 12)
    for u in users[:5]:                                   # bursts: three fails inside 600 s
        t = rng.uniform(0, horizon - 700)
        span = rng.randint(200, 560)
        out += [(t, u, "login", "fail", rng.choice(ips)), (t + span / 2, u, "login", "fail", rng.choice(ips)), (t + span, u, "login", "fail", rng.choice(ips))]
    for u in users[5:8]:                                  # near misses: three fails, span over 600 s
        t = rng.uniform(0, horizon - 1200)
        out += [(t, u, "login", "fail", rng.choice(ips)), (t + 400, u, "login", "fail", rng.choice(ips)), (t + rng.randint(640, 900), u, "login", "fail", rng.choice(ips))]
    for u in users[8:10]:                                 # two fails only
        t = rng.uniform(0, horizon - 100)
        out += [(t, u, "login", "fail", rng.choice(ips)), (t + 50, u, "login", "fail", rng.choice(ips))]
    return out


def _plant2(rng, horizon, ips):
    top = rng.choice(USERS)
    return [(rng.uniform(0, horizon), top, "download", "ok", rng.choice(ips)) for _ in range(rng.randint(13, 19))]


def _plant3(rng, horizon, ips):
    return []


def _plant4(rng, horizon, ips):
    out = [(rng.uniform(0, horizon), "u03", rng.choice(ACTIONS), "ok", rng.choice(ips)) for _ in range(12)]
    return out


def generate(seed: int = 20261114, lines: int = 400) -> tuple[dict, dict]:
    """(files, expected): files maps log_1.txt to log_4.txt to text; expected maps T1 to T5 to integers."""
    logs = [_build(random.Random(seed * 10 + 1), lines, fail_rate=0.12, plant=_plant1),
            _build(random.Random(seed * 10 + 2), lines, fail_rate=0.05, plant=_plant2),
            _build(random.Random(seed * 10 + 3), lines, fail_rate=0.07, plant=_plant3),
            _build(random.Random(seed * 10 + 4), lines, fail_rate=0.05, plant=_plant4)]
    expected = {"T1": q1(logs[0]), "T2": q2(logs[1]), "T3": q3(logs[2]), "T4": q4(logs[3])}
    expected["T5"] = sum(expected.values())
    return {f"log_{n}.txt": text for n, text in enumerate(logs, 1)}, expected


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--lines", type=int, default=400)
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        bad = 0
        for seed in range(1, 41):
            files, expected = generate(seed, 120)
            if q1(files["log_1.txt"]) != q1_brute(files["log_1.txt"]):
                bad += 1
            if not (1 <= expected["T1"] <= 20 and expected["T2"] >= 5 and expected["T4"] > 0):
                bad += 1
        print(f"selfcheck: 40 seeds, {bad} problems")
        return 1 if bad else 0
    files, expected = generate(args.seed, args.lines)
    print(expected, {k: v.count("\n") for k, v in files.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
