import os
from _lib import *
p = f(HDR + row(date="not-a-date"))
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
