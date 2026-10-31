import os
from _lib import *
p = f(HDR + row("1", "0"))
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
