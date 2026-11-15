#!/usr/bin/env python3
"""The regrade as wired into a calibration suite's real grading path (2026-11-15, the three suites after the ticket pair).

Runs named test classes of a suite with the FIRST grade of every delivery's own checks handed a port another socket holds (serve.py's own
pin, E2E_SERVE_PORT), so that every check that starts a candidate through serve.py fails in its first grade, as a candidate does when
another socket takes its port number between free_port() and its bind. With the regrade as shipped the classes pass: each delivery whose
first grade does not agree with what its variant declares is graded once more, alone, without the pin. With `--regrades 0` the same
classes fail, so what is shown is that the suite's own setUpClass (or CaseChecksTest.expect) goes through the regrade, not only that the
helper does what it says (the suites' own SettleTest and RegradeRouteTest show that).

    python3 -B docs/experiments/serve-port-race-20261115/wiring_probe.py SUITE CLASS [CLASS ...] [--regrades N]

SUITE is the file name without test/shiploop-e2e- and .test.py (user-directory, user-chain, brownfield); `--regrades N` replaces the
suite's REGRADES (the default of its settle()) for the run. Prints one JSON line: the suite, its classes, the regrades in force, the
number of deliveries whose first grade was handed the held port, how many deliveries were graded once, twice and more, and the unittest
result. Needs node and lsof, like the suites.
"""

from __future__ import annotations

import collections
import importlib.util
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]


def held_port() -> socket.socket:
    """A listening socket on every address, as a candidate's own, so that a candidate's bind of the same port number fails."""
    sock = socket.socket(socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET)
    if sock.family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::" if sock.family == socket.AF_INET6 else "0.0.0.0", 0))
    sock.listen()
    return sock


def main(argv: list[str]) -> int:
    regrades = None
    if "--regrades" in argv:
        at = argv.index("--regrades")
        regrades = int(argv[at + 1])
        argv = argv[:at] + argv[at + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    suite, classes = argv[0], argv[1:]
    spec = importlib.util.spec_from_file_location("wiring_target", ROOT / "test" / f"shiploop-e2e-{suite}.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["wiring_target"] = module
    spec.loader.exec_module(module)
    if regrades is not None:
        module.settle.__defaults__ = (regrades,)
    holder = held_port()
    port = holder.getsockname()[1]
    real, grades = module.run.run_checks, collections.Counter()

    def run_checks(work, checks, **kwargs):
        first = str(work) not in grades
        grades[str(work)] += 1
        if first:  # the held port goes to the first grade of each delivery only
            kwargs["env"] = {**(kwargs.get("env") or {}), "E2E_SERVE_PORT": str(port)}
        return real(work, checks, **kwargs)

    with mock.patch.object(module.run, "run_checks", run_checks):
        loaded = unittest.defaultTestLoader
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(
            unittest.TestSuite(loaded.loadTestsFromTestCase(getattr(module, name)) for name in classes))
    holder.close()
    print(json.dumps({"suite": suite, "classes": classes, "regrades": module.settle.__defaults__[0], "deliveries": len(grades),
                      "graded_once": sum(1 for n in grades.values() if n == 1), "graded_twice": sum(1 for n in grades.values() if n == 2),
                      "graded_more": sum(1 for n in grades.values() if n > 2), "tests": result.testsRun,
                      "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
                      "ok": result.wasSuccessful()}, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
