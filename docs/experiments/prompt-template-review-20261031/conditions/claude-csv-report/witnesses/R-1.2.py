import os
from _lib import *
a = f(HDR + row()); b = f(HDR + row("1", "0.10", "south"))
c, o, e = run(a, b)
ok(c == 0 and js(o)["rows"] == 2 and js(o)["revenue"] == 7.6, (c, o, e))
