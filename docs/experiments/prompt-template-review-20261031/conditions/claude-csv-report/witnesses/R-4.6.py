import os
from _lib import *
p = f(HDR + row() + b"2024-01-01,north,widget,3\n" + row("1", "0.10", "south"))
c, o, e = run(p)
ok(js(o)["rows"] == 2, (c, o, e))
