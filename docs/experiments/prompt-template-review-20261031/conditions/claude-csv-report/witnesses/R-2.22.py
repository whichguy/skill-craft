import os
from _lib import *
p = f(HDR + row("3", " 2.50 "))
c, o, e = run(p)
ok((c, e, js(o)["revenue"]) == (0, "", 7.5), (c, o, e))
