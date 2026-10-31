import os
from _lib import *
bad = f(HDR + b"2024-01-01,north,widget,3\n"); good = f(HDR + row())
c, o, e = run(bad, good)
ok(c == 2, c)
