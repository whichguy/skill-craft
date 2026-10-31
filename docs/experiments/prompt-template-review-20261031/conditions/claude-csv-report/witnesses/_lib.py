"""Shared helpers for the witnesses: run report.py as a subprocess in a temp dir and assert one condition.

WORK (env) is the copy under test. A witness exits 0 when the condition holds, 1 when it does not.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

WORK = os.environ.get("WORK", "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/claude-csv-report/work")
REPORT = os.path.join(WORK, "report.py")
HDR = b"date,region,product,units,unit_price\n"
D = tempfile.mkdtemp(prefix="wit_")
EMPTY = '{"rows": 0, "revenue": 0.0, "by_region": {}, "by_product": {}}\n'
_n = [0]


def row(units="3", price="2.50", region="north", product="widget", date="2024-01-01"):
    return ("%s,%s,%s,%s,%s\n" % (date, region, product, units, price)).encode("utf-8")


def f(data, name=None):
    """Write bytes to a fresh file in the temp dir; return its path."""
    _n[0] += 1
    path = os.path.join(D, name or ("f%d.csv" % _n[0]))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def run(*args, cwd=None):
    done = subprocess.run([sys.executable, REPORT, *args], capture_output=True, text=True, cwd=cwd, timeout=60)
    return done.returncode, done.stdout, done.stderr


def ok(cond, msg=""):
    if not cond:
        print("WITNESS FAIL: " + str(msg))
        sys.exit(1)


def js(out):
    try:
        return json.loads(out)
    except ValueError:
        ok(False, "stdout is not JSON: %r" % out)


def one_bad(field_units="3", field_price="2.50"):
    """A file with a bad row at line 2: return (path, code, out, err)."""
    p = f(HDR + row(field_units, field_price))
    return (p,) + run(p)
