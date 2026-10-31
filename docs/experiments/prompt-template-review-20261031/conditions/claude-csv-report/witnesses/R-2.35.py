import os
from _lib import *
p = f(b"\xef\xbb\xbf" + HDR + row())
c, o, e = run(p)
j = js(o)
ok((c, e, j["rows"], j["revenue"]) == (0, "", 1, 7.5), (c, o, e))
