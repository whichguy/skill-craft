import os
from _lib import *
p = f(HDR + b"2024-01-01,north,widget,3\n")
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 4\n" % p, e)
