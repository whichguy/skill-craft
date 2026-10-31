import os
from _lib import *
a = f(HDR + row() * 5)
b = f(HDR + row() + b"2024-01-01,north,widget,3\n")
c, o, e = run(a, b)
ok(e == "%s:3: expected 5 columns, got 4\n" % b, e)
