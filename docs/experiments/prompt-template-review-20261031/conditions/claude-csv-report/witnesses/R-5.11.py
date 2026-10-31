import os
from _lib import *
p = f(HDR + b"2024-01-01,north,widget,1," + b"9" * 200000 + b"\n")
c, o, e = run(p)
ok(e.startswith("report.py: error: cannot read %s:" % p) and "Traceback" not in e and o == "" and c == 1, (c, o, e[:200]))
