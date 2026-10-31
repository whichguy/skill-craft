import os
from _lib import *
p = f(HDR + row("1", "5."))
c, o, e = run(p)
ok((c, e, js(o)["revenue"]) == (0, "", 5.0), (c, o, e))
