import os
from _lib import *
c, o, e = run(f(HDR + row("2", "1.50") + row("3", "0.25")))
ok(js(o)["revenue"] == 3.75, o)
