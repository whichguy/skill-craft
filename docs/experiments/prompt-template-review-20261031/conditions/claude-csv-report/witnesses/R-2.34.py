import os
from _lib import *
p = f((HDR + row()).replace(b"\n", b"\r\n"))
c, o, e = run(p)
j = js(o)
ok((c, e, j["rows"], j["revenue"]) == (0, "", 1, 7.5), (c, o, e))
