import os
from _lib import *
a = f(HDR + row()); b = f(HDR + row("1", "0.10", "south"))
c, o, e = run(a, b)
ok(o.count("\n") == 1 and len(o.splitlines()) == 1 and isinstance(js(o), dict), o)
