import os
from _lib import *
c, o, e = run(f(HDR + row("1", "0.004") + row("1", "0.004", "south")))
ok(js(o)["revenue"] == 0.01, o)
