import os
from _lib import *
p = f(HDR + row() + b"2024-01-01,north,widget,3\n")
c, o, e = run(p)
ok(js(o)["rows"] == 1, (c, o, e))
