import os
from _lib import *
p = f(HDR + b"\n" + row())
c, o, e = run(p)
ok(e == "%s:2: expected 5 columns, got 0\n" % p and js(o)["rows"] == 1, (c, o, e))
