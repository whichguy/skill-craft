import os
from _lib import *
p = f(HDR + b"2024-01-01,north,widget,1" + b"0" * 250 + b",1\n")
c, o, e = run(p)
ok(o == "" and c == 1 and "Traceback" not in e, (c, o, e[:200]))
