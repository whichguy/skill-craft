import os
from _lib import *
c, o, e = run(f(HDR + row() + row("x", "1") + row("1", "1")))
ok(js(o)["rows"] == 2, (c, o, e))
