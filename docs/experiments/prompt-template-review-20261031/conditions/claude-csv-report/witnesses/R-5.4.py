import os
from _lib import *
p = f(HDR + row() + b"\xff\n")
c, o, e = run(p)
ok(e.startswith("report.py: error: cannot read %s:" % p), e)
